# Kubernetes 07 — Observing a Running System

When something is wrong, Kubernetes already knows why; you just have to
ask the right object. The order that works: **status** (what state is it
in?), **events** (what did the cluster do?), **logs** (what did the process
say?), then **a shell next to it** (`kubectl debug`).

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

# poll until a jsonpath yields the wanted value (or 90s pass)
wait_for() { # pod jsonpath want
  for _ in $(seq 90); do
    [[ "$(k get pod "$1" -o jsonpath="$2" 2>/dev/null)" == "$3" ]] && return 0
    sleep 1
  done
  return 1
}

echo "=== a process that keeps crashing"
k run crasher --image=busybox:1.36 -- sh -c 'echo "about to fail"; exit 3' >/dev/null
wait_for crasher '{.status.containerStatuses[0].lastState.terminated.exitCode}' 3
k get pod crasher -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}{"\n"}'
k get pod crasher -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}{"\n"}'
echo "--- logs of the previous run (the one that died)"
# kubectl can print "unable to retrieve container logs" while a restart is in flight
for _ in $(seq 30); do
  prev=$(k logs crasher --previous 2>/dev/null) && [[ "$prev" == "about to fail" ]] && break
  sleep 1
done
echo "$prev"

echo "=== an image that cannot be pulled"
k run badimg --image=busybox:no-such-tag --restart=Never >/dev/null
wait_for badimg '{.status.containerStatuses[0].state.waiting.reason}' ImagePullBackOff \
  || wait_for badimg '{.status.containerStatuses[0].state.waiting.reason}' ErrImagePull
k get pod badimg -o jsonpath='{.status.phase}{"\n"}'

echo "=== events explain what the cluster did"
k get events --field-selector involvedObject.name=badimg,reason=Scheduled -o name | wc -l
k get events --field-selector involvedObject.name=badimg,type=Warning -o jsonpath='{.items[*].reason}' \
  | tr ' ' '\n' | sort -u | grep -x Failed

echo "=== describe has the same data, formatted for people"
k describe pod crasher | grep -E '^ +(Exit Code|Reason):' | sort -u

echo "=== several Pods' logs at once, with their names"
k create deployment talk --image=busybox:1.36 --replicas=2 -- sh -c 'echo hello; sleep 3600' >/dev/null
k rollout status deployment/talk --timeout=120s >/dev/null
k logs -l app=talk --prefix | sed 's/talk-[a-z0-9]*-[a-z0-9]*/talk-<id>/' | sort

echo "=== a debug container beside a running one"
k run app --image=busybox:1.36 -- sh -c 'sleep 3600' >/dev/null
k wait --for=condition=Ready pod/app --timeout=90s >/dev/null
k debug app --image=busybox:1.36 --target=app --profile=general -i --quiet -- sh -c 'ps | grep "sleep 3600" | grep -v grep | wc -l'
k get pod app -o jsonpath='{.spec.ephemeralContainers[0].image}{"\n"}'
```

```text output
=== a process that keeps crashing
3
Error
--- logs of the previous run (the one that died)
unable to retrieve container logs for containerd://a6b5a0d8386b2a340581791e2da003e051acd36ead8d027a4040ab2da7ca8f78
=== an image that cannot be pulled
Pending
=== events explain what the cluster did
1
Failed
=== describe has the same data, formatted for people
      Exit Code:    3
      Reason:       Error
=== several Pods' logs at once, with their names
[pod/talk-<id>/busybox] hello
[pod/talk-<id>/busybox] hello
=== a debug container beside a running one
1
busybox:1.36
```

## Details that bite

- **`Phase` is a summary, not a diagnosis.** A Pod in `Pending` might be
  unschedulable, waiting on a volume, or pulling an image. Read
  `status.containerStatuses[].state` and `describe`'s Events section.
- `logs --previous` is the only way to see why a crashed container died,
  because the new instance has fresh logs. It works once per restart; after
  the Pod is deleted the logs are gone. **Ship logs off the node** (Loki,
  Elasticsearch, CloudWatch, Cloud Logging) before you need them.
- Events are **not stored for long**: about an hour by default, and capped.
  Read them promptly, or export them.
- `kubectl logs -l app=x` caps at 5 Pods unless you pass
  `--max-log-requests`, and without `--prefix` you cannot tell lines apart.
- Restart state is a ladder: `ContainerCreating`, `Running`, then
  `Error`/`Completed`, then `CrashLoopBackOff` once the kubelet starts
  delaying restarts (10 s, 20 s, ... up to 5 min).
- Exit code ≥ 128 means a signal: 137 is `SIGKILL` (often OOM, lesson 08),
  143 is `SIGTERM`, 139 is a segfault.
- `kubectl debug` adds an **ephemeral container** to a live Pod. With
  `--target` it shares the process namespace, so you can inspect a
  container that has no shell (distroless images). It cannot be removed;
  the Pod keeps it until recreated. `kubectl debug node/<n>` and
  `kubectl debug <pod> --copy-to=...` cover node and copy-the-Pod cases.
- When `kubectl exec` fails, check the container is actually running:
  `exec` on a crashed or `Completed` container errors out.

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
