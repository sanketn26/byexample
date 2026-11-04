# Kubernetes 04 — Services and DNS

Pods come and go and their IPs change. A **Service** is a stable name and virtual IP that load-balances across whichever Pods currently match its selector. Inside the cluster, DNS resolves `<service>` (same namespace) or `<service>.<namespace>.svc` to it.

## A Service maps `port` to `targetPort`

`port` is what clients call. `targetPort` is the container's port. Swapping them yields "connection refused" from a healthy Pod. The default type, **ClusterIP**, is reachable only inside the cluster. `NodePort` and `LoadBalancer` expose it outward; for HTTP you usually add an Ingress or a Gateway. `kubectl port-forward svc/web 8080:80` reaches a ClusterIP from your laptop.

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
k get service web -o jsonpath='{.spec.type} {.spec.ports[0].port}->{.spec.ports[0].targetPort}{"\n"}'
```

```text output
deployment.apps/web created
service/web created
ClusterIP 80->8080
```

## Endpoints are the ready Pod IPs

A Pod joins the endpoints only once it is Ready. A readiness probe takes a Pod out of rotation without killing it. Empty endpoints mean the selector or readiness is wrong, not the network. `kubectl get endpoints` is the first check when a Service "does not work".

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
          command: ["sh", "-c", "mkdir -p /www && echo ok > /www/index.html && httpd -f -p 8080 -h /www"]
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
k get endpoints web -o jsonpath='{.subsets[0].addresses[*].ip}' | wc -w
```

```text output
deployment.apps/web created
service/web created
2
```

## DNS resolves the Service name

The short name `web` works only in the same namespace. From anywhere else use `web.<namespace>` or `web.<namespace>.svc.cluster.local`. The Service balances **connections**, not requests. A client that holds one keep-alive sticks to one Pod.

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
k run client --image=busybox:1.36 --restart=Never -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/client --timeout=90s >/dev/null
k exec client -- wget -qO- http://web | sed 's/web-.*/web-<pod>/'
k exec client -- wget -qO- "http://web.$ns.svc.cluster.local" | sed 's/web-.*/web-<pod>/'
```

```text output
deployment.apps/web created
service/web created
served by web-<pod>
served by web-<pod>
```

## A selector that matches nothing has no endpoints

The Service is created either way. `subsets` stays empty, which this jsonpath renders as a bare `|`.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - >/dev/null <<'YAML'
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
|
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
