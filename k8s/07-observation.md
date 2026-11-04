# Kubernetes 07 — Observing a Running System

When something is wrong, Kubernetes already knows why. Ask in this order: **status** (what state is it in?), **events** (what did the cluster do?), **logs** (what did the process say?), then **a shell next to it** (`kubectl debug`).

`phase` is a summary, not a diagnosis. A `Pending` Pod might be unschedulable, waiting on a volume, or pulling an image. Read `status.containerStatuses[].state`. The restart ladder is `ContainerCreating`, `Running`, then `Error` or `Completed`, then `CrashLoopBackOff` as the kubelet delays restarts (10s, 20s, up to 5 minutes). An exit code of 128 or more is a signal: 137 is `SIGKILL` (often OOM), 143 is `SIGTERM`, 139 is a segfault. `kubectl exec` fails unless that container is running.

## The container status holds the exit code

`lastState.terminated` is the previous run. `reason: Error` means the process exited non-zero. This is the field to read, not `phase`.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

wait_for() { # pod jsonpath want
  for _ in $(seq 90); do
    [[ "$(k get pod "$1" -o jsonpath="$2" 2>/dev/null)" == "$3" ]] && return 0
    sleep 1
  done
  return 1
}

k run crasher --image=busybox:1.36 -- sh -c 'echo "about to fail"; exit 3' >/dev/null
wait_for crasher '{.status.containerStatuses[0].lastState.terminated.exitCode}' 3
k get pod crasher -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
k get pod crasher -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
```

```text output
3
Error
```

## `logs --previous` is the container that died

The new instance has fresh logs, so `--previous` is the only view of the crash. It works once per restart. After the Pod is deleted the logs are gone, so ship them off the node before you need them. The loop below waits for the text `about to fail`. This capture never got it: the line kubectl printed is the containerd error instead.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

wait_for() { # pod jsonpath want
  for _ in $(seq 90); do
    [[ "$(k get pod "$1" -o jsonpath="$2" 2>/dev/null)" == "$3" ]] && return 0
    sleep 1
  done
  return 1
}

k run crasher --image=busybox:1.36 -- sh -c 'echo "about to fail"; exit 3' >/dev/null
wait_for crasher '{.status.containerStatuses[0].lastState.terminated.exitCode}' 3
for _ in $(seq 30); do
  prev=$(k logs crasher --previous 2>/dev/null) && [[ "$prev" == "about to fail" ]] && break
  sleep 1
done
echo "$prev"
```

```text output
unable to retrieve container logs for containerd://a6b5a0d8386b2a340581791e2da003e051acd36ead8d027a4040ab2da7ca8f78
```

## A bad image stays `Pending`

`ImagePullBackOff` and `ErrImagePull` live on the container's waiting state. `phase` still says `Pending`.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

wait_for() { # pod jsonpath want
  for _ in $(seq 90); do
    [[ "$(k get pod "$1" -o jsonpath="$2" 2>/dev/null)" == "$3" ]] && return 0
    sleep 1
  done
  return 1
}

k run badimg --image=busybox:no-such-tag --restart=Never >/dev/null
wait_for badimg '{.status.containerStatuses[0].state.waiting.reason}' ImagePullBackOff \
  || wait_for badimg '{.status.containerStatuses[0].state.waiting.reason}' ErrImagePull
k get pod badimg -o jsonpath='{.status.phase}{"\n"}'
```

```text output
Pending
```

## Events record what the cluster did

Events are not stored for long: about an hour by default, and capped. Read them promptly or export them. `Failed` here is the pull failure.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

wait_for() { # pod jsonpath want
  for _ in $(seq 90); do
    [[ "$(k get pod "$1" -o jsonpath="$2" 2>/dev/null)" == "$3" ]] && return 0
    sleep 1
  done
  return 1
}

k run badimg --image=busybox:no-such-tag --restart=Never >/dev/null
wait_for badimg '{.status.containerStatuses[0].state.waiting.reason}' ImagePullBackOff \
  || wait_for badimg '{.status.containerStatuses[0].state.waiting.reason}' ErrImagePull
k get events --field-selector involvedObject.name=badimg,reason=Scheduled -o name | wc -l
k get events --field-selector involvedObject.name=badimg,type=Warning -o jsonpath='{.items[*].reason}' \
  | tr ' ' '\n' | sort -u | grep -x Failed
```

```text output
1
Failed
```

## `kubectl describe` formats the same status

`describe` does not know more than the object and its events. It just prints them for a person. The leading spaces are part of that text.

```bash file=n05.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

wait_for() { # pod jsonpath want
  for _ in $(seq 90); do
    [[ "$(k get pod "$1" -o jsonpath="$2" 2>/dev/null)" == "$3" ]] && return 0
    sleep 1
  done
  return 1
}

k run crasher --image=busybox:1.36 -- sh -c 'echo "about to fail"; exit 3' >/dev/null
wait_for crasher '{.status.containerStatuses[0].lastState.terminated.exitCode}' 3
k describe pod crasher | grep -E '^ +(Exit Code|Reason):' | sort -u
```

```text output
      Exit Code:    3
      Reason:       Error
```

## `kubectl logs -l` reads several Pods

Without `--prefix` you cannot tell which Pod printed a line. `-l` stops at 5 Pods unless you pass `--max-log-requests`.

```bash file=n06.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k create deployment talk --image=busybox:1.36 --replicas=2 -- sh -c 'echo hello; sleep 3600' >/dev/null
k rollout status deployment/talk --timeout=120s >/dev/null
k logs -l app=talk --prefix | sed 's/talk-[a-z0-9]*-[a-z0-9]*/talk-<id>/' | sort
```

```text output
[pod/talk-<id>/busybox] hello
[pod/talk-<id>/busybox] hello
```

## `kubectl debug` adds an ephemeral container

`--target` shares that container's process namespace, so you can inspect an image that has no shell. The ephemeral container cannot be removed; it stays until the Pod is recreated. `kubectl debug node/<n>` and `kubectl debug <pod> --copy-to=...` cover a node and a copy of a Pod.

```bash file=n07.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run app --image=busybox:1.36 -- sh -c 'sleep 3600' >/dev/null
k wait --for=condition=Ready pod/app --timeout=90s >/dev/null
k debug app --image=busybox:1.36 --target=app --profile=general -i --quiet -- sh -c 'ps | grep "sleep 3600" | grep -v grep | wc -l'
k get pod app -o jsonpath='{.spec.ephemeralContainers[0].image}{"\n"}'
```

```text output
1
busybox:1.36
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

k run broken --image=busybox:1.36 -- sh -c 'echo "disk full"; exit 28' >/dev/null
# wait until the container has terminated at least once
for _ in $(seq 90); do
  [[ -n "$(k get pod broken -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}' 2>/dev/null)" ]] && break
  sleep 1
done

# Print the exit code of the container's previous termination.
exit_code() {
  echo ""  # TODO
}

# Print the last line the container wrote before it died.
last_words() {
  echo ""  # TODO
}

check "exit code" "$(exit_code)" "28"
check "last words" "$(last_words)" "disk full"
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

k run broken --image=busybox:1.36 -- sh -c 'echo "disk full"; exit 28' >/dev/null
# wait until the container has terminated at least once
for _ in $(seq 90); do
  [[ -n "$(k get pod broken -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}' 2>/dev/null)" ]] && break
  sleep 1
done

exit_code() {
  k get pod broken -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}'
}

last_words() {
  k logs broken --previous | tail -1
}

check "exit code" "$(exit_code)" "28"
check "last words" "$(last_words)" "disk full"
exit $failed
```

</details>

Next: [08 — Resource usage and profiling](08-profiling.md)
