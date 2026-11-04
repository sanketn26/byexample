# Kubernetes 03 — Deployments, Rollouts and Rollback

A **Deployment** keeps N identical Pods running and replaces them gradually when the template changes. It does this through a **ReplicaSet** per template version. Self-healing, scaling, rolling updates, and rollback all come from this one object.

`selector.matchLabels` must match `template.metadata.labels`, and the selector is **immutable** after creation. A mismatch is rejected at apply time. Only a change to `spec.template` starts a rollout. Do not edit the ReplicaSets or Pods a Deployment owns; the controller puts them back.

## `kubectl apply` creates the Deployment

Apply submits the Deployment. `rollout status` waits until the new ReplicaSet is up and exits non-zero if the rollout misses `progressDeadlineSeconds`, so it is the right gate in a deploy script.

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
          command: ["sh", "-c", "sleep 3600"]
YAML
k rollout status deployment/web --timeout=120s >/dev/null && echo "rolled out"
```

```text output
deployment.apps/web created
rolled out
```

## Ready replicas are status, not spec

`spec.replicas` is what you asked for. `status.readyReplicas` is how many are Ready now.

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
          command: ["sh", "-c", "sleep 3600"]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
k get deployment web -o jsonpath='{.status.readyReplicas}{"\n"}'
```

```text output
deployment.apps/web created
2
```

## Deleting a Pod makes the ReplicaSet replace it

The ReplicaSet notices the missing Pod and creates another. The count of Running Pods returns to the spec. A bare Pod would not come back.

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
          command: ["sh", "-c", "sleep 3600"]
YAML
k rollout status deployment/web --timeout=120s >/dev/null
victim=$(k get pods -l app=web -o jsonpath='{.items[0].metadata.name}')
k delete pod "$victim" --wait=true >/dev/null
k rollout status deployment/web --timeout=120s >/dev/null
k get pods -l app=web --field-selector=status.phase=Running -o name | wc -l
```

```text output
deployment.apps/web created
2
```

## `kubectl scale` does not start a rollout

Changing `replicas` rescales the current ReplicaSet. It does not create a new one, because the Pod template did not change.

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
k rollout status deployment/web --timeout=120s >/dev/null
k scale deployment/web --replicas=3
k rollout status deployment/web --timeout=120s >/dev/null
k get deployment web -o jsonpath='{.spec.replicas} {.status.readyReplicas}{"\n"}'
```

```text output
deployment.apps/web created
deployment.apps/web scaled
3 3
```

## `kubectl set image` changes the template

A new template creates a new ReplicaSet and a rolling update. `maxSurge` and `maxUnavailable` default to 25%. Without a readiness probe, "available" only means the container started, so a broken version can still roll out. Prefer editing the YAML and applying it, so the file in git stays the source of truth.

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
k rollout status deployment/web --timeout=120s >/dev/null
k scale deployment/web --replicas=3 >/dev/null
k rollout status deployment/web --timeout=120s >/dev/null
k set image deployment/web main=busybox:1.35
k rollout status deployment/web --timeout=120s >/dev/null && echo "rolled out"
k get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
k get rs -o custom-columns=DESIRED:.spec.replicas,IMAGE:.spec.template.spec.containers[0].image --sort-by=.spec.template.spec.containers[0].image
```

```text output
deployment.apps/web created
deployment.apps/web image updated
rolled out
busybox:1.35
DESIRED   IMAGE
3         busybox:1.35
0         busybox:1.36
```

`DESIRED` is that ReplicaSet's replica count: 3 on the new image because the script scaled first, and 0 on the old image so undo still has that ReplicaSet.

## `kubectl rollout undo` restores the previous ReplicaSet

`undo` points the Deployment at the previous ReplicaSet. Kubernetes keeps old ones up to `revisionHistoryLimit` (default 10). The history count is the number of revisions still stored.

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
k rollout status deployment/web --timeout=120s >/dev/null
k set image deployment/web main=busybox:1.35 >/dev/null
k rollout status deployment/web --timeout=120s >/dev/null
k rollout undo deployment/web
k rollout status deployment/web --timeout=120s >/dev/null && echo "rolled out"
k get deployment web -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
k rollout history deployment/web | grep -c '^[0-9]'
```

```text output
deployment.apps/web created
deployment.apps/web rolled back
rolled out
busybox:1.36
2
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
