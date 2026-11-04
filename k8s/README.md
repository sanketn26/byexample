# Kubernetes by Example

A local cluster and `kubectl`. Each lesson is a series of tiny scripts,
one concept each: `bash n01.sh`, then `n02.sh`. Every script creates a
namespace and deletes it on exit. See [SETUP.md](SETUP.md) for kind.

| # | Lesson | You will practise |
|---|--------|-------------------|
| 01 | [Pods](01-pods.md) | `apply`, `wait`, logs, `exec`, jsonpath |
| 02 | [Labels](02-labels.md) | selectors, `in`, `!=`, `!key`, label updates |
| 03 | [Deployments](03-deployments.md) | replicas, scale, image rollout, undo |
| 04 | [Services](04-services.md) | `port` vs `targetPort`, endpoints, DNS |
| 05 | [Config and Secrets](05-config-secrets.md) | ConfigMap, Secret mounts, base64 |
| 06 | [Networking](06-networking.md) | Pod IP, ClusterIP, headless DNS, NetworkPolicy |
| 07 | [Observation](07-observation.md) | status, events, previous logs, `debug` |
| 08 | [Profiling](08-profiling.md) | requests, limits, QoS, cgroup quota |
| 09 | [Advanced observation](09-advanced-observation.md) | `/readyz`, watches, API and cAdvisor metrics |
