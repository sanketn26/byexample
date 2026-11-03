# Kubernetes 04 — Services and DNS

Pods come and go and their IPs change. A **Service** is a stable name and
virtual IP that load-balances across whichever Pods currently match its
selector. Inside the cluster, DNS resolves `<service>` (same namespace) or
`<service>.<namespace>.svc` to it.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

# A tiny web server: busybox httpd serving one file.
k apply -f - <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
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
          command: ["sh", "-c", "mkdir -p /www && echo \"served by $(hostname)\" > /www/index.html && httpd -f -p 8080 -h /www"]
          ports:
            - containerPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: web
spec:
  selector: {app: web}
  ports:
    - port: 80
      targetPort: 8080
YAML
k rollout status deployment/web --timeout=120s >/dev/null

echo "--- the Service and its type"
k get service web -o jsonpath='{.spec.type} {.spec.ports[0].port}->{.spec.ports[0].targetPort}{"\n"}'

echo "--- endpoints: one per ready Pod"
k get endpoints web -o jsonpath='{.subsets[0].addresses[*].ip}' | wc -w

echo "--- call the Service by DNS name from another Pod"
k run client --image=busybox:1.36 --restart=Never -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/client --timeout=90s >/dev/null
k exec client -- wget -qO- http://web | sed 's/web-.*/web-<pod>/'
k exec client -- wget -qO- "http://web.$ns.svc.cluster.local" | sed 's/web-.*/web-<pod>/'

echo "--- a selector that matches nothing has no endpoints"
k apply -f - <<'YAML' >/dev/null
apiVersion: v1
kind: Service
metadata:
  name: orphan
spec:
  selector: {app: nothing}
  ports:
    - port: 80
YAML
k get endpoints orphan -o jsonpath='{.subsets}{"|\n"}'
```

```text output
deployment.apps/web created
service/web created
--- the Service and its type
ClusterIP 80->8080
--- endpoints: one per ready Pod
2
--- call the Service by DNS name from another Pod
served by web-<pod>
served by web-<pod>
--- a selector that matches nothing has no endpoints
|
```

## Details that bite

- `port` is what clients call; `targetPort` is the container's port. Mixing
  them up gives "connection refused" with a perfectly healthy Pod.
- The default type, **ClusterIP**, is reachable only inside the cluster.
  `NodePort` and `LoadBalancer` expose it outward; for HTTP you normally
  add an **Ingress** or Gateway on top.
- A Pod only appears in the endpoints once it is **Ready**. That is how a
  readiness probe (lesson 07) takes a Pod out of rotation without killing it.
- DNS short names (`web`) work only within the same namespace. From
  another namespace use `web.<ns>` or the full `web.<ns>.svc.cluster.local`.
- The Service load-balances **connections**, not requests. A client that
  holds one keep-alive connection sticks to one Pod.
- `k get endpoints` is the first thing to check when a Service "does not
  work": empty means selector or readiness, not networking.
- `kubectl port-forward svc/web 8080:80` is the quick way to reach a
  ClusterIP Service from your laptop while debugging.

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
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 2
  selector:
    matchLabels: {app: site}
  template:
    metadata:
      labels: {app: site}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /www && echo ok > /www/index.html && httpd -f -p 9090 -h /www"]
YAML
k rollout status deployment/site --timeout=120s >/dev/null

# Create a Service "site" that exposes port 80 and forwards to the
# containers' port 9090 (select app=site).
expose_site() {
  :  # TODO
}

expose_site
k run client --image=busybox:1.36 --restart=Never -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/client --timeout=90s >/dev/null 2>&1
check "endpoints" "$(k get endpoints site -o jsonpath='{.subsets[0].addresses[*].ip}' 2>/dev/null | wc -w | tr -d ' ')" "2"
check "reachable" "$(k exec client -- wget -qO- -T 5 http://site 2>/dev/null)" "ok"
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
apiVersion: apps/v1
kind: Deployment
metadata:
  name: site
spec:
  replicas: 2
  selector:
    matchLabels: {app: site}
  template:
    metadata:
      labels: {app: site}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "mkdir -p /www && echo ok > /www/index.html && httpd -f -p 9090 -h /www"]
YAML
k rollout status deployment/site --timeout=120s >/dev/null

expose_site() {
  k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Service
metadata:
  name: site
spec:
  selector: {app: site}
  ports:
    - port: 80
      targetPort: 9090
YAML
}

expose_site
k run client --image=busybox:1.36 --restart=Never -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/client --timeout=90s >/dev/null 2>&1
check "endpoints" "$(k get endpoints site -o jsonpath='{.subsets[0].addresses[*].ip}' 2>/dev/null | wc -w | tr -d ' ')" "2"
check "reachable" "$(k exec client -- wget -qO- -T 5 http://site 2>/dev/null)" "ok"
exit $failed
```

</details>

Next: [05 — ConfigMaps and Secrets](05-config-secrets.md)
