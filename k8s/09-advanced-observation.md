# Kubernetes 09 — Advanced Observation

Everything `kubectl` shows comes from the API server, and the API server and kubelet both publish their own telemetry. Metric text is Prometheus exposition format: `name{label="v"} value`. You normally scrape it. Prometheus reads `/metrics` from the API server, `/metrics/cadvisor` and `/metrics/resource` from each kubelet, and `kube-state-metrics` turns object state (desired versus ready replicas, Pod phases) into series the raw endpoints do not have.

Counters only go up; you look at their rate. Gauges are a snapshot. Histograms (`..._bucket`, `_sum`, `_count`) feed `histogram_quantile`. A label with unbounded values (user id, request path) creates millions of series and sinks Prometheus. Audit logs answer "who deleted that?"; events and container logs cannot. They are a separate API-server flag, off by default on most self-managed clusters, CloudWatch on EKS, and Cloud Audit Logs on GKE. Tracing is the third pillar. The cluster does not provide it; applications emit spans.

## `/livez` and `/readyz` report process health

`/livez` is liveness. `/readyz?verbose` lists each check; the last line is the summary. `kubectl get --raw` is a GET against the API server with your kubeconfig credentials.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

kubectl get --raw /livez
echo
kubectl get --raw '/readyz?verbose' | tail -1
```

```text output
ok
readyz check passed
```

## `-v=6` prints the HTTP request

`-v=6` logs the request, `-v=8` adds response bodies, and `-v=9` adds a curl equivalent. That is the fastest way to see which API a command uses. The host and the namespace are rewritten below so the line stays stable.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k get pods -v=6 2>&1 | grep -o 'GET https://[^ ]*' | sed "s#https://[^/]*#API#; s#$ns#<ns>#"
```

```text output
GET API/api/v1/namespaces/<ns>/pods?limit=500
```

## `kubectl get --raw` returns the object

The path is the HTTP path kubectl would call. `jq` prints the same fields the table is built from.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run viewer --image=busybox:1.36 -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/viewer --timeout=90s >/dev/null
kubectl get --raw "/api/v1/namespaces/$ns/pods/viewer" | jq -r '.kind, .status.phase'
```

```text output
Pod
Running
```

## `kubectl get -w` is a stream of events

`--output-watch-events` prefixes each line with `ADDED`, `MODIFIED`, or `DELETED`. `kubectl` re-lists and reconnects when the stream ends. A hand-rolled watch must track `resourceVersion` or it can miss events. Prefer an informer (client-go, kopf, controller-runtime) to a raw watch loop.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k get pods -w --output-watch-events --no-headers > watch.log 2>/dev/null &
watcher=$!
sleep 2
k run streamed --image=busybox:1.36 -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/streamed --timeout=90s >/dev/null
k delete pod streamed --wait=false >/dev/null
for _ in $(seq 60); do grep -q '^DELETED.*streamed' watch.log && break; sleep 1; done
kill "$watcher" 2>/dev/null || true
awk '$2 == "streamed" && !seen[$1]++ {print $1}' watch.log
```

```text output
ADDED
MODIFIED
DELETED
```

## `apiserver_request_total` counts LIST calls

The script sums the API server's LIST counter for pods, issues five lists, and expects the counter to move by at least 5. The captured line from this cluster does not match that echo. It is copied here unchanged because the cluster was not reachable to re-run it.

```bash file=n05.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

requests() {
  kubectl get --raw /metrics \
    | awk '/^apiserver_request_total\{/ && /verb="LIST"/ && /resource="pods"/ {s += $NF} END {print s + 0}'
}
before=$(requests)
for _ in 1 2 3 4 5; do k get pods -o name >/dev/null; done
after=$(requests)
(( after - before >= 5 )) && echo "counter grew by at least 5"
```

```text output
counter grew by at least 5: 1
```

## cAdvisor exposes per-container series

`/metrics/cadvisor` is proxied through the kubelet. `container_memory_working_set_bytes` is the working set for this Pod, and `container_cpu_usage_seconds_total` is a counter. Direct `nodes/<node>/proxy` access is privileged: the RBAC verb is `get` on `nodes/proxy`. Grant it only to monitoring agents.

```bash file=n06.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k run viewer --image=busybox:1.36 -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/viewer --timeout=90s >/dev/null
node=$(k get pod viewer -o jsonpath='{.spec.nodeName}')
kubectl get --raw "/api/v1/nodes/$node/proxy/metrics/cadvisor" > cadvisor.txt
grep -q "^container_memory_working_set_bytes{.*namespace=\"$ns\".*pod=\"viewer\"" cadvisor.txt && echo "cadvisor sees the Pod"
grep '^# TYPE container_cpu_usage_seconds_total' cadvisor.txt
```

```text output
cadvisor sees the Pod
# TYPE container_cpu_usage_seconds_total counter
```

## API server `/metrics` describes the cluster

`apiserver_request_duration_seconds` is the latency histogram. On this capture the histogram grep printed nothing, and the etcd series were present. `etcd_` lines are the API server's view of its store.

```bash file=n07.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

kubectl get --raw /metrics | grep -q '^# TYPE apiserver_request_duration_seconds histogram' && echo "latency histogram present"
kubectl get --raw /metrics | grep -c '^etcd_' | awk '{print ($1 > 0) ? "etcd metrics present" : "no etcd metrics"}'
```

```text output
etcd metrics present
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

k run subject --image=busybox:1.36 --labels=tier=cache -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/subject --timeout=90s >/dev/null 2>&1

# Using only `kubectl get --raw` and jq (no `kubectl get pod`), print the
# Pod's "tier" label.
tier() {
  echo ""  # TODO
}

# Using the raw API, print the number of Pods in the namespace.
pod_count() {
  echo 0  # TODO
}

# Print "ok" if the API server's readiness endpoint reports healthy.
ready() {
  echo ""  # TODO
}

check "label" "$(tier)" "cache"
check "count" "$(pod_count)" "1"
check "readyz" "$(ready)" "ok"
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

k run subject --image=busybox:1.36 --labels=tier=cache -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/subject --timeout=90s >/dev/null 2>&1

tier() {
  kubectl get --raw "/api/v1/namespaces/$ns/pods/subject" | jq -r '.metadata.labels.tier'
}

pod_count() {
  kubectl get --raw "/api/v1/namespaces/$ns/pods" | jq '.items | length'
}

ready() {
  kubectl get --raw /readyz
}

check "label" "$(tier)" "cache"
check "count" "$(pod_count)" "1"
check "readyz" "$(ready)" "ok"
exit $failed
```

</details>

Next: the track is not finished; see [the README](README.md).
