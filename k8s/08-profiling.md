# Kubernetes 08 — Resource Usage and Profiling

"Is it slow because of my code or because of its limits?" Kubernetes enforces CPU and memory through Linux cgroups. You can see that from the kubelet's stats, from the cgroup files inside the container, and from the Pod status after a kill. None of those needs `metrics-server`.

`kubectl top` does need `metrics-server`, which kind does not ship. Its numbers are about 15 seconds old, fine for a quick check or an HPA. For history, scrape cAdvisor. The working set (`memory.workingSetBytes` on the kubelet summary at `/api/v1/nodes/<node>/proxy/stats/summary`) is what eviction uses, not RSS. To profile application code, expose its profiler and `kubectl port-forward` to it, or run the tool in `kubectl debug --target`. The cluster only tells you the container is hot.

## QoS class comes from requests and limits

Requests are what the scheduler reserves. Limits are what the kernel enforces. Equal requests and limits make `Guaranteed`. Requests below limits make `Burstable`. Neither makes `BestEffort`, which is evicted first under node pressure, then `Burstable`. Autoscalers act on requests, not limits. A Pod with no CPU request can never trip a CPU HPA.

```bash file=n01.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

pod() { # name cpu-req mem-req cpu-lim mem-lim cmd
  local res="" cmd=${6//\"/\\\"}
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

pod besteffort "" "" "" "" "sleep 3600"
pod burstable 50m 32Mi 200m 64Mi "sleep 3600"
pod guaranteed 100m 64Mi 100m 64Mi "sleep 3600"
for p in besteffort burstable guaranteed; do
  echo "$p -> $(k get pod $p -o jsonpath='{.status.qosClass}')"
done
```

```text output
besteffort -> BestEffort
burstable -> Burstable
guaranteed -> Guaranteed
```

## A CPU limit is a cgroup quota

`cpu.max` is the cgroup v2 quota and the period, in microseconds. 100m is `10000 100000`: 10 ms of CPU in each 100 ms period. On cgroup v1 the same files live under `/sys/fs/cgroup/cpu/`. `memory.max` is the memory limit next to it.

```bash file=n02.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: guaranteed}
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sleep", "3600"]
      resources:
        requests: {cpu: 100m, memory: 64Mi}
        limits: {cpu: 100m, memory: 64Mi}
YAML
k wait --for=condition=Ready pod/guaranteed --timeout=90s >/dev/null
k exec guaranteed -- cat /sys/fs/cgroup/cpu.max
```

```text output
10000 100000
```

## A CPU limit throttles; it does not kill

Go over the quota and the process is paused for the rest of that 100 ms period. Check `nr_throttled` and `throttled_usec` in `cpu.stat`. Climbing numbers look like latency spikes with low average CPU. Many teams set a CPU request and no CPU limit for that reason.

```bash file=n03.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

k apply -f - >/dev/null <<'YAML'
apiVersion: v1
kind: Pod
metadata: {name: spinner}
spec:
  containers:
    - name: main
      image: busybox:1.36
      command: ["sh", "-c", "while :; do :; done"]
      resources:
        requests: {cpu: 100m, memory: 16Mi}
        limits: {cpu: 100m, memory: 32Mi}
YAML
k wait --for=condition=Ready pod/spinner --timeout=90s >/dev/null
for _ in $(seq 40); do
  n=$(k exec spinner -- sh -c 'sed -n "s/^nr_throttled //p" /sys/fs/cgroup/cpu.stat')
  [[ "${n:-0}" -gt 0 ]] && break
  sleep 1
done
[[ "${n:-0}" -gt 0 ]] && echo "throttled: yes"
```

```text output
throttled: yes
```

## This memory-limit Pod never applies

A memory limit is a cliff: cross it and the container is killed (`OOMKilled`, exit 137). The command below was meant to show that. Its quotes break the YAML, so `apply` rejects the object and the OOM killer never runs. The kubelet summary and `top` steps that followed this command in the original script did not run either.

```bash file=n04.sh
#!/usr/bin/env bash
set -euo pipefail
ns=byex-$$
kubectl create namespace "$ns" >/dev/null
trap 'kubectl delete namespace "$ns" --wait=false >/dev/null' EXIT
k() { kubectl -n "$ns" "$@"; }

pod() { # name cpu-req mem-req cpu-lim mem-lim cmd
  local res="" cmd=${6//\"/\\\"}
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

set +e
pod hog 10m 16Mi 100m 32Mi "awk 'BEGIN { s = sprintf(\"%1000000s\", \"x\"); for (i = 0; i < 100; i++) a[i] = s; system(\"sleep 3600\") }'"
set -e
```

```text output
error: error parsing STDIN: error converting YAML to JSON: yaml: line 8: found character that cannot start any token
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
