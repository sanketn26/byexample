# Kubernetes 02 — Labels and Selectors

Kubernetes has no foreign keys. Objects find each other through **labels**:
free-form `key=value` pairs on metadata, matched by **selectors**. A
Service finds its Pods this way, a Deployment finds the Pods it owns this
way, and so do you when you run `kubectl get -l`.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

# Three Pods with different labels. `run` is the imperative shortcut.
k run web1 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600
k run web2 --image=busybox:1.36 --labels=app=web,tier=frontend -- sleep 3600
k run db1  --image=busybox:1.36 --labels=app=db,tier=backend   -- sleep 3600

echo "--- equality selector"
k get pods -l app=web -o name

echo "--- set-based selector"
k get pods -l 'tier in (frontend,backend)' -o name

echo "--- AND: comma means both must match"
k get pods -l app=web,tier=backend -o name | wc -l

echo "--- negation and existence"
k get pods -l 'app!=web' -o name
k get pods -l '!canary' -o name | wc -l

echo "--- show labels as columns"
k get pods -L app,tier -o custom-columns=NAME:.metadata.name,APP:.metadata.labels.app,TIER:.metadata.labels.tier

echo "--- relabel, then select again"
k label pod web2 canary=true tier=edge --overwrite
k get pods -l canary=true -o name
k get pod web2 -o jsonpath='{.metadata.labels}{"\n"}'

echo "--- delete by selector"
k delete pods -l app=web --wait=false
k wait --for=delete pod -l app=web --timeout=90s
k get pods -o name
```

```text output
pod/web1 created
pod/web2 created
pod/db1 created
--- equality selector
pod/web1
pod/web2
--- set-based selector
pod/db1
pod/web1
pod/web2
--- AND: comma means both must match
0
--- negation and existence
pod/db1
3
--- show labels as columns
NAME   APP   TIER
db1    db    backend
web1   web   frontend
web2   web   frontend
--- relabel, then select again
pod/web2 labeled
pod/web2
{"app":"web","canary":"true","tier":"edge"}
--- delete by selector
pod "web1" deleted
pod "web2" deleted
pod/web1 condition met
pod/web2 condition met
pod/db1
```

## Details that bite

- Label keys and values are limited: 63 characters, alphanumerics plus
  `-_.`, start and end alphanumeric. No spaces. Use **annotations** for
  free text.
- Selectors do **not** match across namespaces. Every `-l` query is scoped
  to one namespace unless you pass `-A`.
- Comma is AND. There is no OR except `in (a,b)` over **one** key.
- A Service's `selector` or a Deployment's `matchLabels` that is slightly
  wrong does not error. It just matches nothing, and the symptom is
  "no endpoints" or "0 pods". When something that should find Pods finds
  none, compare the selector against `k get pods --show-labels`.
- Changing a Pod's labels can *detach* it from a Deployment or Service.
  That is a useful trick: relabel a misbehaving Pod and it stops receiving
  traffic but stays alive to inspect.
- Common convention: `app.kubernetes.io/name`, `.../instance`,
  `.../version`. Tools such as Helm rely on them.

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
