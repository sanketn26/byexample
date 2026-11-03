# Kubernetes 01 — Pods and kubectl

A **Pod** is the smallest thing Kubernetes runs: one or more containers
that share a network and storage. You describe the Pod you *want* in YAML,
`kubectl apply` sends it to the API server, and the cluster makes it so.

Every example here runs in a throwaway **namespace** that the script
deletes on exit, so lessons never collide. The cluster is a local
[kind](https://kind.sigs.k8s.io) cluster: `kind create cluster`.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

# Declare a Pod. apply is idempotent: run it twice, get the same state.
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

# Wait for a condition instead of sleeping and hoping.
k wait --for=condition=Ready pod/hello --timeout=90s

# Read the container's stdout.
k logs hello

# Run a command inside the running container.
k exec hello -- sh -c 'echo $((6 * 7))'

# Pick fields out of the object. custom-columns is stable, tabular output.
k get pod hello -o custom-columns=NAME:.metadata.name,PHASE:.status.phase,IMAGE:.spec.containers[0].image

# jsonpath extracts exactly one value, ideal for scripts.
k get pod hello -o jsonpath='{.spec.restartPolicy}{"\n"}'

# A second apply of the same file changes nothing.
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
k get pods -o name | wc -l
```

```text output
pod/hello created
pod/hello condition met
hello from hello
42
NAME    PHASE     IMAGE
hello   Running   busybox:1.36
Always
pod/hello unchanged
pod "hello" deleted
0
```

## Details that bite

- A Pod's `spec` is **mostly immutable**. You cannot change `command` or
  `image` of a running Pod's identity the way you edit a file; for
  anything but the image you delete and recreate it. That is why you
  normally run Pods through a Deployment (lesson 03).
- A bare Pod is not rescheduled if its node dies. Nothing owns it.
- `kubectl run` and `kubectl create` are imperative. `kubectl apply -f` is
  declarative and is what belongs in version control.
- `kubectl wait` fails with a non-zero exit on timeout, so it composes
  with `set -e`.
- `image: busybox` means `busybox:latest`, which changes under you. Pin a
  tag (or better, a digest).
- Use `-o jsonpath` or `-o custom-columns` in scripts. The default table
  output is for humans and its columns change between versions.
- Always pass `-n <namespace>`. Without it kubectl uses the namespace of
  your current context, which is how people delete the wrong thing.

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
