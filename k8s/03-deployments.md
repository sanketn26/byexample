# Kubernetes 03 — Deployments, Rollouts and Rollback

A **Deployment** keeps N identical Pods running and replaces them
gradually when the template changes. It does this through a **ReplicaSet**
per template version. Self-healing, scaling, rolling updates and rollback
all come from this one object.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }
# progress lines vary run to run, so print one stable line instead
rolled_out() { k rollout status deployment/web --timeout=120s >/dev/null && echo "rolled out"; }

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
          command: ["sh", "-c", "sleep 3600"]
YAML
rolled_out

echo "--- ready replicas"
k get deployment web -o jsonpath='{.status.readyReplicas}{"\n"}'

echo "--- self-healing: delete a Pod, a replacement appears"
victim=$(k get pods -l app=web -o jsonpath='{.items[0].metadata.name}')
k delete pod "$victim" --wait=true >/dev/null
rolled_out >/dev/null
k get pods -l app=web --field-selector=status.phase=Running -o name | wc -l

echo "--- scale"
k scale deployment/web --replicas=3
rolled_out >/dev/null
k get deployment web -o jsonpath='{.spec.replicas} {.status.readyReplicas}{"\n"}'

echo "--- rolling update: change the template"
k set image deployment/web main=busybox:1.35
rolled_out
k get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
k get rs -o custom-columns=DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image --sort-by=.spec.template.spec.containers[0].image

echo "--- rollback"
k rollout undo deployment/web
rolled_out
k get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
k rollout history deployment/web | grep -c '^[0-9]'
```

```text output
deployment.apps/web created
rolled out
--- ready replicas
2
--- self-healing: delete a Pod, a replacement appears
2
--- scale
deployment.apps/web scaled
3 3
--- rolling update: change the template
deployment.apps/web image updated
rolled out
busybox:1.35
DESIRED   IMAGE
3         busybox:1.35
0         busybox:1.36
--- rollback
deployment.apps/web rolled back
rolled out
busybox:1.36
2
```

## Details that bite

- `selector.matchLabels` must match `template.metadata.labels`, and the
  selector is **immutable** after creation. A mismatch is rejected at
  apply time, which is a kindness.
- Only a change to `spec.template` creates a new rollout. Changing
  `replicas` does not; it just rescales the current ReplicaSet.
- Rolling updates honour `maxSurge` and `maxUnavailable` (default 25%).
  Without a **readiness probe** (lesson 07), "available" means only "the
  container started", so a broken new version can still roll out.
- `rollout undo` goes to the previous ReplicaSet, which Kubernetes keeps
  according to `revisionHistoryLimit` (default 10).
- Never edit the ReplicaSets or Pods a Deployment owns; the controller
  will revert you.
- `kubectl rollout status` exits non-zero when the rollout fails its
  deadline (`progressDeadlineSeconds`), which makes it the right gate in a
  deploy script.
- Prefer editing YAML and `apply`-ing it over `kubectl set image` in real
  use, so the file in git stays the source of truth.

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

# Create a Deployment "api" with 2 replicas of busybox:1.36 running
# `sleep 3600`, labelled app=api. Wait for it to be rolled out.
deploy() {
  :  # TODO
}

# Scale "api" to 4 replicas and wait until all are ready.
grow() {
  :  # TODO
}

# Print the number of ready replicas of "api".
ready() {
  echo 0  # TODO
}

deploy
check "initial" "$(k get deploy api -o jsonpath='{.status.readyReplicas}' 2>/dev/null)" "2"
grow
check "scaled" "$(ready)" "4"
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

deploy() {
  k apply -f - >/dev/null <<'YAML'
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
  selector:
    matchLabels: {app: api}
  template:
    metadata:
      labels: {app: api}
    spec:
      containers:
        - name: main
          image: busybox:1.36
          command: ["sh", "-c", "sleep 3600"]
YAML
  k rollout status deployment/api --timeout=120s >/dev/null
}

grow() {
  k scale deployment/api --replicas=4 >/dev/null
  k rollout status deployment/api --timeout=120s >/dev/null
}

ready() {
  k get deploy api -o jsonpath='{.status.readyReplicas}'
}

deploy
check "initial" "$(k get deploy api -o jsonpath='{.status.readyReplicas}' 2>/dev/null)" "2"
grow
check "scaled" "$(ready)" "4"
exit $failed
```

</details>

Next: [04 — Services](04-services.md)
