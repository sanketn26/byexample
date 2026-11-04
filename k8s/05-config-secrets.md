# Kubernetes 05 — ConfigMaps and Secrets

Keep configuration out of the image. A **ConfigMap** holds plain settings, a **Secret** holds sensitive ones. Both reach a Pod as environment variables or as files in a mounted volume. Each is capped at about 1 MiB and lives in one namespace; a Pod can mount only those from its own.

## `--dry-run=client` prints YAML and applies nothing

`kubectl create --dry-run=client -o yaml` is the fast way to get an object you can edit. Nothing is sent to the API, so `creationTimestamp` stays null.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

kubectl create configmap demo --from-literal=a=1 --dry-run=client -o yaml
```

```text output
apiVersion: v1
data:
  a: "1"
kind: ConfigMap
metadata:
  creationTimestamp: null
  name: demo
```

## A ConfigMap key becomes an environment variable

`configMapKeyRef` copies one key. `envFrom` copies every key. The process reads environment variables once, at start. Changing the ConfigMap does not change a running container's env. Mounted files do update, after a delay of up to a minute, unless the mount uses `subPath` (which never updates). To roll Pods when config changes, put a hash of the config in a template annotation or run `kubectl rollout restart`. A missing ConfigMap or key leaves the Pod in `CreateContainerConfigError`. Set `optional: true` only when the app really copes without it.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k create configmap app-config --from-literal=MODE=prod --from-literal=LEVEL=info
k create secret generic db --from-literal=user=admin --from-literal=password=s3cr3t
k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      env:
        - name: MODE
          valueFrom:
            configMapKeyRef: {name: app-config, key: MODE}
        - name: DB_USER
          valueFrom:
            secretKeyRef: {name: db, key: user}
      envFrom:
        - configMapRef: {name: app-config}
YAML
k wait --for=condition=Ready pod/app --timeout=90s >/dev/null
k exec app -- sh -c 'echo "$MODE $LEVEL $DB_USER"'
```

```text output
configmap/app-config created
secret/db created
pod/app created
prod info admin
```

## A ConfigMap mount is one file per key

`--from-file=app.conf` uses the filename as the key. The mount directory contains that file.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

printf 'listen=8080\nworkers=2\n' > app.conf
k create configmap app-files --from-file=app.conf
k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - {name: files, mountPath: /etc/app}
  volumes:
    - name: files
      configMap: {name: app-files}
YAML
k wait --for=condition=Ready pod/app --timeout=90s >/dev/null
k exec app -- cat /etc/app/app.conf
```

```text output
configmap/app-files created
pod/app created
listen=8080
workers=2
```

## A Secret mount is files with a mode

`defaultMode: 0400` is the file mode inside the container. Never put secrets in `command`, `args`, or images. They show up in `kubectl describe`, in `ps`, and in registries.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k create secret generic db --from-literal=user=admin --from-literal=password=s3cr3t
k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: app
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "sleep 3600"]
      volumeMounts:
        - {name: creds, mountPath: /etc/db, readOnly: true}
  volumes:
    - name: creds
      secret: {secretName: db, defaultMode: 0400}
YAML
k wait --for=condition=Ready pod/app --timeout=90s >/dev/null
k exec app -- cat /etc/db/password; echo
k exec app -- stat -L -c '%a' /etc/db/password
```

```text output
secret/db created
pod/app created
s3cr3t
400
```

## A Secret is base64, not encryption

Anyone who can `get secret` can read it. `.data` is base64. `.type` for a generic Secret is `Opaque`. Protect Secrets with RBAC, turn on encryption at rest in the API server, and for real systems use an external store synced in by a controller.

```bash file=n05.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k create secret generic db --from-literal=user=admin --from-literal=password=s3cr3t
k get secret db -o jsonpath='{.data.password}{"\n"}'
k get secret db -o jsonpath='{.data.password}' | base64 -d; echo
k get secret db -o jsonpath='{.type}{"\n"}'
```

```text output
secret/db created
czNjcjN0
s3cr3t
Opaque
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

# Create a ConfigMap "greet" with key msg=hello and a Secret "token" with
# key value=abc123.
make_config() {
  :  # TODO
}

# Create a Pod "reader" (busybox:1.36) that prints $MSG (from the ConfigMap
# key, via an env var named MSG) and the contents of the Secret file
# /etc/token/value, space-separated, then sleeps.
make_pod() {
  :  # TODO
}

make_config
make_pod
k wait --for=condition=Ready pod/reader --timeout=90s >/dev/null 2>&1
check "logs" "$(k logs reader 2>/dev/null)" "hello abc123"
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

make_config() {
  k create configmap greet --from-literal=msg=hello >/dev/null
  k create secret generic token --from-literal=value=abc123 >/dev/null
}

make_pod() {
  k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: reader
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo \"$MSG $(cat /etc/token/value)\"; sleep 3600"]
      env:
        - name: MSG
          valueFrom:
            configMapKeyRef: {name: greet, key: msg}
      volumeMounts:
        - {name: tok, mountPath: /etc/token}
  volumes:
    - name: tok
      secret: {secretName: token}
YAML
}

make_config
make_pod
k wait --for=condition=Ready pod/reader --timeout=90s >/dev/null 2>&1
check "logs" "$(k logs reader 2>/dev/null)" "hello abc123"
exit $failed
```

</details>

Next: [06 — Networking](06-networking.md)
