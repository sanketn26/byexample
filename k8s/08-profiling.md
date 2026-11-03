# Kubernetes 08 — Resource Usage and Profiling

"Is it slow because of my code or because of its limits?" Kubernetes
enforces CPU and memory through Linux **cgroups**, so you can measure the
truth from three places: the **kubelet's stats**, the **cgroup files inside
the container**, and the **Pod's status** after a kill. None needs
`metrics-server`.

## Example

```bash file=example.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

pod() { # name cpu-req mem-req cpu-lim mem-lim cmd
  local res="" cmd=${6//\"/\\\"}   # escape quotes for the YAML string
  [[ -n "$2" ]] && res="resources: {requests: {cpu: $2, memory: $3}, limits: {cpu: $4, memory: $5}}"
  k apply -f - >/dev/null <<YAML
apiVersion: v1
kind: Pod
metadata: {name: $1}
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "$cmd"]
      ${res}
YAML
}

echo "=== QoS class is derived from requests and limits"
pod besteffort "" "" "" "" "sleep 3600"
pod burstable 50m 32Mi 200m 64Mi "sleep 3600"
pod guaranteed 100m 64Mi 100m 64Mi "sleep 3600"
for p in besteffort burstable guaranteed; do
  echo "$p -> $(k get pod $p -o jsonpath='{.status.qosClass}')"
done

echo "=== a CPU limit becomes a cgroup quota"
k wait --for=condition=Ready pod/guaranteed --timeout=90s >/dev/null
k exec guaranteed -- cat /sys/fs/cgroup/cpu.max        # quota period, in microseconds

echo "=== a busy loop under a 100m limit gets throttled"
pod spinner 100m 16Mi 100m 32Mi 'while :; do :; done'
k wait --for=condition=Ready pod/spinner --timeout=90s >/dev/null
for _ in $(seq 40); do
  n=$(k exec spinner -- sh -c 'sed -n "s/^nr_throttled //p" /sys/fs/cgroup/cpu.stat')
  [[ "${n:-0}" -gt 0 ]] && break
  sleep 1
done
[[ "${n:-0}" -gt 0 ]] && echo "throttled: yes"

echo "=== a memory limit is enforced by the kernel's OOM killer"
pod hog 10m 16Mi 100m 32Mi "awk 'BEGIN { s = sprintf(\"%1000000s\", \"x\"); for (i = 0; i < 100; i++) a[i] = s; system(\"sleep 3600\") }'"
for _ in $(seq 90); do
  r=$(k get pod hog -o jsonpath='{.status.containerStatuses[0].lastState.terminated.reason}' 2>/dev/null)
  [[ -n "$r" ]] && break
  sleep 1
done
echo "reason=$r exit=$(k get pod hog -o jsonpath='{.status.containerStatuses[0].lastState.terminated.exitCode}')"

echo "=== live numbers from the kubelet, no metrics-server needed"
node=$(k get pod guaranteed -o jsonpath='{.spec.nodeName}')
kubectl get --raw "/api/v1/nodes/$node/proxy/stats/summary" \
  | jq -r --arg ns "$ns" '.pods[] | select(.podRef.namespace==$ns and .podRef.name=="guaranteed")
      | .containers[0] | "cpu counter: \(.cpu.usageCoreNanoSeconds > 0)\nworking set > 0: \(.memory.workingSetBytes > 0)"'

echo "=== inside the container, with the tools it already has"
k exec guaranteed -- sh -c 'top -b -n 1 | head -1 | cut -c1-4'
k exec guaranteed -- sh -c 'echo "memory.max=$(cat /sys/fs/cgroup/memory.max)"'
```

```text output
=== QoS class is derived from requests and limits
besteffort -> BestEffort
burstable -> Burstable
guaranteed -> Guaranteed
=== a CPU limit becomes a cgroup quota
10000 100000
=== a busy loop under a 100m limit gets throttled
throttled: yes
=== a memory limit is enforced by the kernel's OOM killer
error: error parsing STDIN: error converting YAML to JSON: yaml: line 8: found character that cannot start any token
```

## Details that bite

- **Requests** are what the scheduler reserves; **limits** are what the
  kernel enforces. A Pod with `requests < limits` is `Burstable` and is the
  first evicted under node pressure after `BestEffort` ones.
- A **memory limit is a cliff**: go over and the container is killed
  (`OOMKilled`, exit 137). A **CPU limit is a throttle**: go over and the
  process is paused for the rest of each 100 ms period. Throttling looks
  like random latency spikes with low average CPU.
- Check `nr_throttled` / `throttled_usec` in `cpu.stat`. If it climbs,
  raise the limit or drop it. Many teams set CPU *requests* but no CPU
  *limits* for exactly this reason.
- `kubectl top` needs `metrics-server`, which kind does not ship. It gives
  coarse numbers (about 15 s old) for HPA and quick checks. For history use
  Prometheus scraping cAdvisor (lesson 09).
- The **working set** (`memory.workingSetBytes`) is what the kubelet uses
  to decide on eviction, not RSS or "used". It includes recently used page
  cache that cannot be reclaimed.
- Cgroup v2 paths (`/sys/fs/cgroup/cpu.max`) apply on modern kernels; on
  cgroup v1 nodes they live under `/sys/fs/cgroup/cpu/`.
- To profile *application* code, expose its profiler (Go `net/http/pprof`,
  JFR, `py-spy`) and `kubectl port-forward pod/x 6060` to it, or run the
  tool in a `kubectl debug --target` ephemeral container. The cluster only
  tells you the container is hot, not which function.
- Autoscalers act on **requests**, not limits. A Pod with no CPU request
  can never trigger a CPU-based HPA.

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

# Create a Pod "tuned" (busybox:1.36, sleep 3600) with CPU request and limit
# both 250m and memory request and limit both 48Mi, so its QoS class is
# Guaranteed.
make_pod() {
  :  # TODO
}

make_pod
k wait --for=condition=Ready pod/tuned --timeout=90s >/dev/null 2>&1
check "qos" "$(k get pod tuned -o jsonpath='{.status.qosClass}' 2>/dev/null)" "Guaranteed"
# 250m of CPU is a quota of 25000us per 100000us period
check "quota" "$(k exec tuned -- cat /sys/fs/cgroup/cpu.max 2>/dev/null)" "25000 100000"
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
metadata: {name: tuned}
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sleep", "3600"]
      resources:
        requests: {cpu: 250m, memory: 48Mi}
        limits: {cpu: 250m, memory: 48Mi}
YAML
}

make_pod
k wait --for=condition=Ready pod/tuned --timeout=90s >/dev/null 2>&1
check "qos" "$(k get pod tuned -o jsonpath='{.status.qosClass}' 2>/dev/null)" "Guaranteed"
# 250m of CPU is a quota of 25000us per 100000us period
check "quota" "$(k exec tuned -- cat /sys/fs/cgroup/cpu.max 2>/dev/null)" "25000 100000"
exit $failed
```

</details>

Next: [09 — Advanced observation](09-advanced-observation.md)
