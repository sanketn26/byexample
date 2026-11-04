# Kubernetes 02 — Labels and Selectors

Kubernetes has no foreign keys. Objects find each other through **labels**: free-form `key=value` pairs on metadata, matched by **selectors**. A Service finds its Pods this way, a Deployment finds the Pods it owns this way, and so do you with `kubectl get -l`.

A key or value is at most 63 characters: alphanumerics plus `-_.`, starting and ending alphanumeric. No spaces. Put free text in **annotations**. Selectors do not match across namespaces unless you pass `-A`.

## An equality selector matches one value

`kubectl run --labels` sets labels on the new Pod. `-l app=web` keeps objects whose `app` label is exactly `web`. A selector that is slightly wrong does not error. It matches nothing, and the symptom is "no endpoints" or "0 pods". Compare it with `kubectl get pods --show-labels`.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600
k get pods -l app=web -o name
```

```text output
pod/web1 created
pod/web2 created
pod/db1 created
pod/web1
pod/web2
```

## `in` is a set on one key

`in (a,b)` is the only OR, and it covers one key. A comma between selectors is AND, not OR.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k get pods -l 'tier in (frontend,backend)' -o name
```

```text output
pod/db1
pod/web1
pod/web2
```

## A comma means both must match

Each extra term narrows the set. `app=web` and `tier=backend` do not overlap, so the count is zero.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k get pods -l app=web,tier=backend -o name 2>/dev/null | wc -l
```

```text output
0
```

## `!=` drops one value

`app!=web` keeps Pods whose `app` is not `web`, and Pods that have no `app` label. `!key` is the separate test for "this key is absent".

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k get pods -l 'app!=web' -o name
```

```text output
pod/db1
```

## `!key` selects a missing label

`!canary` matches Pods that do not have that key at all. None of these three do.

```bash file=n05.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k get pods -l '!canary' -o name | wc -l
```

```text output
3
```

## `-L` adds label columns

`-L app,tier` asks for those labels. `custom-columns` names the same fields explicitly, which is the stable form. The usual keys are `app.kubernetes.io/name`, `app.kubernetes.io/instance`, and `app.kubernetes.io/version`. Helm relies on them.

```bash file=n06.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k get pods -L app,tier -o custom-columns=NAME:.metadata.name,APP:.metadata.labels.app,TIER:.metadata.labels.tier
```

```text output
NAME   APP   TIER
db1    db    backend
web1   web   frontend
web2   web   frontend
```

## `kubectl label` changes labels on a live Pod

`--overwrite` replaces a key that already exists. Relabeling can detach a Pod from a Deployment or Service: it stops receiving traffic and stays up to inspect.

```bash file=n07.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k label pod web2 canary=true tier=edge --overwrite
k get pods -l canary=true -o name
k get pod web2 -o jsonpath='{.metadata.labels}{"\n"}'
```

```text output
pod/web2 labeled
pod/web2
{"app":"web","canary":"true","tier":"edge"}
```

## `kubectl delete -l` deletes by selector

The selector chooses the Pods. `wait --for=delete` returns when they are gone. `db1` does not match `app=web`, so it stays.

```bash file=n08.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600 >/dev/null
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600 >/dev/null
k delete pods -l app=web --wait=false
k wait --for=delete pod -l app=web --timeout=90s
k get pods -o name
```

```text output
pod "web1" deleted
pod "web2" deleted
pod/web1 condition met
pod/web2 condition met
pod/db1
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

k run a --image=busybox:1.36 --labels=env=prod,team=red   -- sleep 3600 >/dev/null
k run b --image=busybox:1.36 --labels=env=prod,team=blue  -- sleep 3600 >/dev/null
k run c --image=busybox:1.36 --labels=env=dev,team=red    -- sleep 3600 >/dev/null
k run d --image=busybox:1.36 --labels=env=staging         -- sleep 3600 >/dev/null

# Print the names (one per line, sorted, without "pod/") of prod Pods
# owned by the red team.
prod_red() {
  echo ""  # TODO
}

# Print the names of Pods whose env is NOT prod, space-separated.
not_prod() {
  echo ""  # TODO
}

# Print the names of Pods that have a "team" label at all, space-separated.
has_team() {
  echo ""  # TODO
}

check "prod+red" "$(prod_red)" "a"
check "not prod" "$(not_prod)" "c d"
check "has team" "$(has_team)" "a b c"
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

k run a --image=busybox:1.36 --labels=env=prod,team=red   -- sleep 3600 >/dev/null
k run b --image=busybox:1.36 --labels=env=prod,team=blue  -- sleep 3600 >/dev/null
k run c --image=busybox:1.36 --labels=env=dev,team=red    -- sleep 3600 >/dev/null
k run d --image=busybox:1.36 --labels=env=staging         -- sleep 3600 >/dev/null

names() { k get pods "$@" -o jsonpath='{range .items[*]}{.metadata.name}{"\n"}{end}' | sort; }

prod_red() {
  names -l env=prod,team=red
}

not_prod() {
  names -l env!=prod | paste -sd' '
}

has_team() {
  names -l team | paste -sd' '
}

check "prod+red" "$(prod_red)" "a"
check "not prod" "$(not_prod)" "c d"
check "has team" "$(has_team)" "a b c"
exit $failed
```

</details>

Next: [03 — Deployments](03-deployments.md)
