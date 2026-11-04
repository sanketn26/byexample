# Kubernetes 06 — Networking: Pod IPs, DNS and NetworkPolicy

Kubernetes networking has three rules: every Pod gets its own IP, every Pod can reach every other Pod without NAT, and Services give groups of Pods a stable name. By default everything may talk to everything. **NetworkPolicy** is how you take that away.

A ClusterIP exists only as iptables or IPVS rules on each node. You cannot ping it, and it answers only on the declared ports. Short DNS names use the `search` line in `/etc/resolv.conf` and `ndots:5`, so an external name is tried with several suffixes first. A trailing dot (`example.com.`) skips that.

## A Pod IP is reachable directly

No NAT sits between Pods. Another Pod can call the target's IP and port.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /w && echo ok > /w/index.html && httpd -f -p 8080 -h /w"]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k run other --image=busybox:1.36 --labels=role=other -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/other --timeout=90s >/dev/null
pod_ip=$(k get pods -l app=web -o jsonpath='{.items[0].status.podIP}')
k exec other -- wget -qO- -T 3 "http://$pod_ip:8080"
```

```text output
deployment.apps/web created
ok
```

## Service DNS resolves to the ClusterIP

An absolute name (trailing dot) skips the search-domain list. `nslookup` exits 1 on that name, so the script tolerates the failure and compares the address it did print.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /w && echo ok > /w/index.html && httpd -f -p 8080 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: 8080}]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k run other --image=busybox:1.36 --labels=role=other -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/other --timeout=90s >/dev/null
cluster_ip=$(k get service web -o jsonpath='{.spec.clusterIP}')
dns_ip=$(k exec other -- nslookup "web.$ns.svc.cluster.local." 2>/dev/null | awk '/^Name:/{f=1} f && /^Address/{print $NF; exit}' || true)
[[ "$dns_ip" == "$cluster_ip" ]] && echo "web -> ClusterIP"
```

```text output
deployment.apps/web created
service/web created
web -> ClusterIP
```

## A headless Service returns one DNS record per Pod

`clusterIP: None` means there is no virtual IP. DNS answers with the Pod IPs instead.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /w && echo ok > /w/index.html && httpd -f -p 8080 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: web-pods}
spec:
  clusterIP: None
  selector: {app: web}
  ports: [{port: 80, targetPort: 8080}]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k run other --image=busybox:1.36 --labels=role=other -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/other --timeout=90s >/dev/null
k exec other -- nslookup "web-pods.$ns.svc.cluster.local." 2>/dev/null | awk '/^Name:/{f=1} f && /^Address/{n++} END{print n " records"}' || true
```

```text output
deployment.apps/web created
service/web-pods created
2 records
```

## EndpointSlices back every Service

Every Service has an EndpointSlice. `ready` is the condition that decides whether a Pod receives traffic.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /w && echo ok > /w/index.html && httpd -f -p 8080 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: 8080}]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k get endpointslices -l kubernetes.io/service-name=web -o jsonpath='{.items[0].endpoints[*].conditions.ready}{"\n"}'
```

```text output
deployment.apps/web created
service/web created
true true
```

## With no policy, every Pod can connect

Until a NetworkPolicy selects a Pod, nothing is denied.

```bash file=n05.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /w && echo ok > /w/index.html && httpd -f -p 8080 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: 8080}]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k run trusted --image=busybox:1.36 --labels=role=trusted -- sleep 3600 >/dev/null
k run other   --image=busybox:1.36 --labels=role=other   -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/trusted pod/other --timeout=90s >/dev/null
can_reach() { k exec "$1" -- wget -qO- -T 2 http://web >/dev/null 2>&1; }
can_reach other   && echo "other: allowed"
can_reach trusted && echo "trusted: allowed"
```

```text output
deployment.apps/web created
service/web created
other: allowed
trusted: allowed
```

## A NetworkPolicy is an allow list

Policies are additive. A Pod selected by no policy is open. A Pod selected by any Ingress policy admits only what some policy allows. There is no deny rule. The usual starting point is a default-deny (`podSelector: {}`, `policyTypes: [Ingress, Egress]`, no rules), then allow what you need. A `podSelector` matches only the same namespace; add a `namespaceSelector` (the label `kubernetes.io/metadata.name` is set automatically) for other namespaces. Two selectors in one list item are AND; two items are OR. Policies see the Pod IP and `targetPort` after DNAT, which is why this rule names 8080, not 80. If you deny egress, allow UDP and TCP 53 to `kube-dns` in `kube-system`, or every lookup times out. None of this does anything unless the CNI enforces it (Calico, Cilium, kindnet). On EKS enable the VPC CNI policy support or install Calico or Cilium; on GKE enable network policy or Dataplane V2. Otherwise the API accepts the object and the dataplane ignores it.

```bash file=n06.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /w && echo ok > /w/index.html && httpd -f -p 8080 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: 8080}]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k run trusted --image=busybox:1.36 --labels=role=trusted -- sleep 3600 >/dev/null
k run other   --image=busybox:1.36 --labels=role=other   -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/trusted pod/other --timeout=90s >/dev/null
k apply -f - >/dev/null <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: web-ingress}
spec:
  podSelector: {matchLabels: {app: web}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {role: trusted}}
      ports: [{port: 8080}]
YAML
can_reach() { k exec "$1" -- wget -qO- -T 2 http://web >/dev/null 2>&1; }
for _ in $(seq 30); do can_reach other || break; sleep 1; done
can_reach other   || echo "other: blocked"
can_reach trusted && echo "trusted: allowed"
```

```text output
deployment.apps/web created
service/web created
other: blocked
trusted: allowed
```

## Exercises

```bash file=exercise.sh
#!/usr/bin/env bash
set -uo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: db, labels: {app: db}}
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "mkdir -p /w && echo rows > /w/index.html && httpd -f -p 5432 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: db}
spec:
  selector: {app: db}
  ports: [{port: 5432}]
YAML
k run api --image=busybox:1.36 --labels=tier=api -- sleep 3600 >/dev/null
k run cron --image=busybox:1.36 --labels=tier=batch -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/db pod/api pod/cron --timeout=90s >/dev/null 2>&1

# Create a NetworkPolicy "db-from-api" so that Pods labelled app=db accept
# TCP 5432 only from Pods labelled tier=api.
protect_db() {
  :  # TODO
}

can_reach() { k exec "$1" -- wget -qO- -T 2 http://db:5432 2>/dev/null; }

protect_db
# wait for the policy to take effect on the blocked client
for _ in $(seq 30); do [[ -z "$(can_reach cron)" ]] && break; sleep 1; done
check "api allowed" "$(can_reach api)" "rows"
check "batch blocked" "$(can_reach cron)" ""
exit $failed
```

<details><summary>Solution</summary>

```bash file=solution.sh
#!/usr/bin/env bash
set -uo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }
failed=0
check() { # label got want
  if [[ "$2" == "$3" ]]; then echo "PASS $1"; else echo "FAIL $1: got [$2], want [$3]"; failed=1; fi
}

k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: db, labels: {app: db}}
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "mkdir -p /w && echo rows > /w/index.html && httpd -f -p 5432 -h /w"]
---
apiVersion: v1
kind: Service
metadata: {name: db}
spec:
  selector: {app: db}
  ports: [{port: 5432}]
YAML
k run api --image=busybox:1.36 --labels=tier=api -- sleep 3600 >/dev/null
k run cron --image=busybox:1.36 --labels=tier=batch -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/db pod/api pod/cron --timeout=90s >/dev/null 2>&1

protect_db() {
  k apply -f - >/dev/null <<'YAML'
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: db-from-api}
spec:
  podSelector: {matchLabels: {app: db}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {tier: api}}
      ports:
        - {protocol: TCP, port: 5432}
YAML
}

can_reach() { k exec "$1" -- wget -qO- -T 2 http://db:5432 2>/dev/null; }

protect_db
# wait for the policy to take effect on the blocked client
for _ in $(seq 30); do [[ -z "$(can_reach cron)" ]] && break; sleep 1; done
check "api allowed" "$(can_reach api)" "rows"
check "batch blocked" "$(can_reach cron)" ""
exit $failed
```

</details>

Next: [07 — Observing a running system](07-observation.md)
