# Kubernetes 05 — ConfigMaps and Secrets

Keep configuration out of the image. A **ConfigMap** holds plain settings,
a **Secret** holds sensitive ones. Both reach a Pod as environment
variables or as files in a mounted volume.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

echo "--- generate YAML without touching the cluster"
kubectl create configmap demo --from-literal=a=1 --dry-run=client -o yaml

printf 'listen=8080\nworkers=2\n' > app.conf
k create configmap app-config --from-literal=MODE=prod --from-literal=LEVEL=info
k create configmap app-files --from-file=app.conf
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
        - name: MODE                     # one key, renamed if you like
          valueFrom:
            configMapKeyRef: {name: app-config, key: MODE}
        - name: DB_USER
          valueFrom:
            secretKeyRef: {name: db, key: user}
      envFrom:                           # every key becomes a variable
        - configMapRef: {name: app-config}
      volumeMounts:
        - {name: files, mountPath: /etc/app}
        - {name: creds, mountPath: /etc/db, readOnly: true}
  volumes:
    - name: files
      configMap: {name: app-files}
    - name: creds
      secret: {secretName: db, defaultMode: 0400}
YAML
k wait --for=condition=Ready pod/app --timeout=90s >/dev/null

echo "--- as environment variables"
k exec app -- sh -c 'echo "$MODE $LEVEL $DB_USER"'

echo "--- as files"
k exec app -- cat /etc/app/app.conf
k exec app -- cat /etc/db/password; echo
k exec app -- stat -L -c '%a' /etc/db/password

echo "--- a Secret is base64, not encryption"
k get secret db -o jsonpath='{.data.password}{"\n"}'
k get secret db -o jsonpath='{.data.password}' | base64 -d; echo
k get secret db -o jsonpath='{.type}{"\n"}'
```

```text output
--- generate YAML without touching the cluster
apiVersion: v1
data:
  a: "1"
kind: ConfigMap
metadata:
  creationTimestamp: null
  name: demo
configmap/app-config created
configmap/app-files created
secret/db created
pod/app created
--- as environment variables
prod info admin
--- as files
listen=8080
workers=2
s3cr3t
400
--- a Secret is base64, not encryption
czNjcjN0
s3cr3t
Opaque
```

## Details that bite

- **Secrets are only base64.** Anyone who can `get secret` can read them.
  Protect them with RBAC (lesson 11), turn on encryption at rest in the API
  server, and for real systems use an external store (Vault, AWS Secrets
  Manager, GCP Secret Manager) synced in by a controller.
- Environment variables are read **once at container start**. Changing the
  ConfigMap does not update a running container's env. Mounted files do
  update, after a delay of up to a minute, unless you used `subPath`
  (which never updates).
- To roll Pods when config changes, put a hash of the config in a template
  annotation (Helm does this with `checksum/config`) or use
  `kubectl rollout restart`.
- A missing ConfigMap or key makes the Pod hang in
  `CreateContainerConfigError`. Mark it `optional: true` only when the app
  truly copes without it.
- ConfigMaps and Secrets are limited to about 1 MiB and live in one
  namespace; a Pod can only mount ones from its own.
- Never put secrets in `command` or `args` or in images. They show up in
  `kubectl describe`, in `ps` and in registries.
- `--dry-run=client -o yaml` is the fastest way to get correct YAML to edit.

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
