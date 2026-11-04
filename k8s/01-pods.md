# Kubernetes 01 — Pods and kubectl

A **Pod** is the smallest thing Kubernetes runs: one or more containers that share a network and storage. You describe the Pod you want in YAML, `kubectl apply` sends it to the API server, and the cluster makes it so.

Every script creates a namespace `byex-$$` and deletes it on exit. `k` is `kubectl -n` that namespace. Without `-n`, kubectl uses the namespace of your current context, which is how people delete the wrong thing. These lessons expect a local [kind](https://kind.sigs.k8s.io) cluster.

## `kubectl apply` is idempotent

`apply` records the object you want. A second apply of the same spec prints `unchanged`. `kubectl run` and `kubectl create` are imperative; `apply -f` is what belongs in git. Pin a tag: `busybox` alone means `busybox:latest`. A Pod `spec` is mostly immutable. You cannot change `command` in place; for anything but the image you delete and recreate. That is why Pods normally sit under a Deployment.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
```

```text output
pod/hello created
pod/hello unchanged
```

## `kubectl wait` exits non-zero on timeout

Wait on a condition instead of sleeping. A timeout fails the script, so `wait` composes with `set -e`.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k wait --for=condition=Ready pod/hello --timeout=90s
```

```text output
pod/hello created
pod/hello condition met
```

## `kubectl logs` reads container stdout

`logs` prints what the container wrote. The shell inside the Pod expands `hostname`, and a Pod's hostname is its name.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k wait --for=condition=Ready pod/hello --timeout=90s >/dev/null
k logs hello
```

```text output
pod/hello created
hello from hello
```

## `kubectl exec` runs a command in the container

`exec` starts a process in the running container. `--` ends kubectl's own flags.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k wait --for=condition=Ready pod/hello --timeout=90s >/dev/null
k exec hello -- sh -c 'echo $((6 * 7))'
```

```text output
pod/hello created
42
```

## `custom-columns` is for scripts

The default table is for humans and its columns change between versions. Name the fields you want.

```bash file=n05.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k wait --for=condition=Ready pod/hello --timeout=90s >/dev/null
k get pod hello -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,IMAGE:.spec.containers[0].image
```

```text output
pod/hello created
NAME    PHASE     IMAGE
hello   Running   busybox:1.36
```

## `jsonpath` prints one field

`jsonpath` extracts a single value. A Pod's `restartPolicy` defaults to `Always`.

```bash file=n06.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k get pod hello -o jsonpath='{.spec.restartPolicy}{"\n"}'
```

```text output
pod/hello created
Always
```

## `kubectl delete` removes the Pod

A bare Pod has no owner. If its node dies, nothing reschedules it. `--wait` returns when the object is gone.

```bash file=n07.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: hello
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo hello from $(hostname); sleep 3600"]
YAML
k delete pod hello --wait=true
k get pods -o name 2>/dev/null | wc -l
```

```text output
pod/hello created
pod "hello" deleted
0
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

# Create a Pod named "probe" running busybox:1.36 that prints "ready" and
# then sleeps. Use `k apply -f -` with a heredoc.
make_pod() {
  :  # TODO
}

# Print the Pod's phase (use jsonpath).
phase() {
  echo ""  # TODO
}

# Print the Pod's log output.
say() {
  echo ""  # TODO
}

make_pod
k wait --for=condition=Ready pod/probe --timeout=90s >/dev/null 2>&1
check "phase" "$(phase)" "Running"
check "logs" "$(say)" "ready"
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

make_pod() {
  k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Pod
metadata:
  name: probe
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "echo ready; sleep 3600"]
YAML
}

phase() {
  k get pod probe -o jsonpath='{.status.phase}'
}

say() {
  k logs probe
}

make_pod
k wait --for=condition=Ready pod/probe --timeout=90s >/dev/null 2>&1
check "phase" "$(phase)" "Running"
check "logs" "$(say)" "ready"
exit $failed
```

</details>

Next: [02 — Labels and selectors](02-labels.md)
