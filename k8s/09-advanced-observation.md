# Kubernetes 09 — Advanced Observation

Everything `kubectl` shows comes from the **API server**, and the API
server and kubelet both publish their own telemetry. This lesson goes
below the friendly commands: raw API paths, watch streams, request
tracing, and the Prometheus-format metrics that real monitoring scrapes.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

echo "=== health endpoints"
kubectl get --raw /livez
echo
kubectl get --raw '/readyz?verbose' | tail -1

echo "=== every kubectl command is an HTTP request (-v=6 shows it)"
k get pods -v=6 2>&1 | grep -o 'GET https://[^ ]*' | sed "s#https://[^/]*#API#; s#$ns#<ns>#"

echo "=== the raw API returns exactly what kubectl formats"
k run viewer --image=busybox:1.36 -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/viewer --timeout=90s >/dev/null
kubectl get --raw "/api/v1/namespaces/$ns/pods/viewer" | jq -r '.kind, .status.phase'

echo "=== a watch is a stream of events, not a poll"
k get pods -w --output-watch-events --no-headers > watch.log 2>/dev/null &
watcher=$!
sleep 2
k run streamed --image=busybox:1.36 -- sleep 3600 >/dev/null
k wait --for=condition=Ready pod/streamed --timeout=90s >/dev/null
k delete pod streamed --wait=false >/dev/null
for _ in $(seq 60); do grep -q '^DELETED.*streamed' watch.log && break; sleep 1; done
kill "$watcher" 2>/dev/null || true
awk '$2 == "streamed" && !seen[$1]++ {print $1}' watch.log

echo "=== observe the observer: API server request counters"
requests() {  # total LIST requests the API server has counted for pods
  kubectl get --raw /metrics \
    | awk '/^apiserver_request_total\{/ && /verb="LIST"/ && /resource="pods"/ {s += $NF} END {print s + 0}'
}
before=$(requests)
for _ in 1 2 3 4 5; do k get pods -o name >/dev/null; done
after=$(requests)
(( after - before >= 5 )) && echo "counter grew by at least 5"

echo "=== kubelet's cAdvisor metrics: per-container series for our Pod"
node=$(k get pod viewer -o jsonpath='{.spec.nodeName}')
kubectl get --raw "/api/v1/nodes/$node/proxy/metrics/cadvisor" > cadvisor.txt
grep -q "^container_memory_working_set_bytes{.*namespace=\"$ns\".*pod=\"viewer\"" cadvisor.txt && echo "cadvisor sees the Pod"
grep '^# TYPE container_cpu_usage_seconds_total' cadvisor.txt

echo "=== metrics that describe the cluster itself"
kubectl get --raw /metrics | grep -q '^# TYPE apiserver_request_duration_seconds histogram' && echo "latency histogram present"
kubectl get --raw /metrics | grep -c '^etcd_' | awk '{print ($1 > 0) ? "etcd metrics present" : "no etcd metrics"}'
```

```text output
=== health endpoints
ok
readyz check passed
=== every kubectl command is an HTTP request (-v=6 shows it)
GET API/api/v1/namespaces/<ns>/pods?limit=500
=== the raw API returns exactly what kubectl formats
Pod
Running
=== a watch is a stream of events, not a poll
ADDED
MODIFIED
DELETED
=== observe the observer: API server request counters
counter grew by at least 5: 1
=== kubelet's cAdvisor metrics: per-container series for our Pod
cadvisor sees the Pod
# TYPE container_cpu_usage_seconds_total counter
=== metrics that describe the cluster itself
etcd metrics present
```

## Details that bite

- Metric text is **Prometheus exposition format**: `name{label="v"} value`.
  You normally never grep it; Prometheus scrapes `/metrics` from the API
  server, `/metrics/cadvisor` and `/metrics/resource` from each kubelet,
  and `kube-state-metrics` turns object *state* (desired vs ready replicas,
  Pod phases) into metrics the raw endpoints do not have.
- Counters only go up; you look at their **rate**. Gauges are a snapshot.
  Histograms (`..._bucket`, `_sum`, `_count`) are how you get latency
  percentiles via `histogram_quantile`.
- `kubectl get -w` re-lists and reconnects when the stream ends; a hand
  rolled watch must track `resourceVersion` or it can miss events. Prefer
  informers/controllers (client-go, kopf, controller-runtime) to raw watch
  loops.
- Verbosity: `-v=6` prints requests, `-v=8` adds response bodies, `-v=9`
  adds curl equivalents. It is the fastest way to learn which API a
  command uses, and to write the same call in code.
- **Audit logs** (who did what, when) are a separate, API-server flag,
  off by default on most self-managed clusters and delivered to CloudWatch
  on EKS and Cloud Audit Logs on GKE. They are the answer to "who deleted
  that?"; events and logs cannot tell you.
- Direct `nodes/<n>/proxy/...` access is a **privileged** operation. The
  RBAC verb is `get` on `nodes/proxy`; grant it only to monitoring agents.
- Cardinality bites: a label with unbounded values (user id, request path)
  on a metric creates millions of series and sinks Prometheus.
- Tracing (OpenTelemetry) is the third pillar beside metrics and logs. The
  cluster does not provide it; applications emit spans to a collector.

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
