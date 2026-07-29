---
name: kubernetes-iperf3-throughput
description: Test bidirectional TCP network throughput between two Kubernetes contexts using temporary iperf3 server and client pods. Use for iperf3, Kubernetes bandwidth, cross-cluster throughput, or network performance tests.
---

# Kubernetes iperf3 Throughput

Use this workflow to measure TCP throughput in both directions between two Kubernetes contexts. Each direction runs a temporary `iperf3` server pod in the destination context and a client pod in the source context. Report the client's aggregate receive bandwidth as the result for that direction.

## Before Running

1. Ask for the two `kubectl` context names if they were not supplied. Name them `context-a` and `context-b` in the result.

2. Ask for a namespace if one was not supplied. Use a dedicated, writable namespace when possible. Default to `default` only after confirmation.

3. Ask how the client cluster can reach the server cluster. Default to a temporary `LoadBalancer` Service. If either cluster cannot provision a reachable load balancer, ask for the supported alternative, such as a preconfigured ingress, a routable node IP and NodePort, or private inter-cluster connectivity.

4. Confirm the test duration and parallel stream count. Default to 30 seconds and one stream. Use more streams only when the user wants to test aggregate capacity rather than a single TCP flow.

5. State that this creates temporary pods and a network service in both clusters, and that `iperf3` traffic can consume substantial bandwidth. Do not start until the user has requested the test.

## Preconditions

- Verify both contexts exist and are distinct:

```bash
kubectl config get-contexts -o name
```

- Verify access and namespace permissions in each context:

```bash
kubectl --context <context-a> -n <namespace> auth can-i create pods
kubectl --context <context-a> -n <namespace> auth can-i create services
kubectl --context <context-b> -n <namespace> auth can-i create pods
kubectl --context <context-b> -n <namespace> auth can-i create services
```

- Never rely on pod IPs for a cross-cluster test. Pod CIDRs are commonly not routed between clusters.

## Test One Direction

Run this section once for `context-a -> context-b`, then again with the contexts reversed. Use a unique run ID, such as `iperf3-<UTC timestamp>`, and append `-a-to-b` or `-b-to-a` to resource names. Keep the same image in both contexts, for example `networkstatic/iperf3:latest`, unless the user specifies a vetted image.

1. Create the server pod in the destination context.

```bash
kubectl --context <destination-context> -n <namespace> run <server-name> \
  --image=networkstatic/iperf3:latest \
  --restart=Never \
  --labels="app=<server-name>,run=<run-id>" \
  --command -- iperf3 -s

kubectl --context <destination-context> -n <namespace> wait \
  --for=condition=Ready pod/<server-name> --timeout=120s
```

2. Expose the server using the agreed reachable endpoint strategy. For a load balancer:

```bash
kubectl --context <destination-context> -n <namespace> expose pod <server-name> \
  --name <service-name> \
  --port 5201 \
  --target-port 5201 \
  --labels="run=<run-id>" \
  --type LoadBalancer
```

Wait until the service has an ingress IP or hostname. Inspect it with:

```bash
kubectl --context <destination-context> -n <namespace> get service <service-name> -o jsonpath='{.status.loadBalancer.ingress[0].ip}{.status.loadBalancer.ingress[0].hostname}{"\n"}'
```

If no endpoint appears before the agreed timeout, stop that direction, collect `kubectl describe service`, and either troubleshoot the platform or use the alternative endpoint strategy. Do not silently test a different path.

3. Run the client pod in the source context. Use `--json` so the bandwidth result can be extracted without parsing human-formatted output. The client exits after the test, so wait for completion rather than readiness.

```bash
kubectl --context <source-context> -n <namespace> run <client-name> \
  --image=networkstatic/iperf3:latest \
  --restart=Never \
  --labels="run=<run-id>" \
  --command -- iperf3 -c <server-endpoint> -p 5201 -t <seconds> -P <streams> --json

kubectl --context <source-context> -n <namespace> wait \
  --for=jsonpath='{.status.phase}'=Succeeded pod/<client-name> --timeout=<seconds-plus-120>s
```

4. Get the JSON result and report the aggregate receiving bandwidth. For a normal client-to-server TCP test, use `end.sum_received.bits_per_second` from the client output. Convert bits per second to Gbit/s by dividing by `1000000000`; keep the unrounded value in saved output if requested.

```bash
kubectl --context <source-context> -n <namespace> logs pod/<client-name> > <client-name>.json
jq '{bits_per_second: .end.sum_received.bits_per_second, gbit_per_second: (.end.sum_received.bits_per_second / 1000000000)}' < <client-name>.json
```

Do not use per-stream values or the sender summary as the directional result. `sum_received` is the receiver-side aggregate and best represents traffic delivered to the destination.

5. Check for failures before treating a result as valid. Inspect the client pod status and JSON error field, if present. Report retransmissions from `end.sum_sent.retransmits` when available; high retransmissions can make the throughput result less representative.

```bash
kubectl --context <source-context> -n <namespace> get pod <client-name>
jq '{error, received_bps: .end.sum_received.bits_per_second, retransmits: .end.sum_sent.retransmits}' < <client-name>.json
```

6. Delete resources for that direction after collecting the logs. If cleanup fails, report the resource names and contexts so they can be removed manually.

```bash
kubectl --context <source-context> -n <namespace> delete pod <client-name> --ignore-not-found
kubectl --context <destination-context> -n <namespace> delete service <service-name> --ignore-not-found
kubectl --context <destination-context> -n <namespace> delete pod <server-name> --ignore-not-found
```

## Report

Report both measurements with unambiguous direction labels:

```text
context-a -> context-b: <average aggregate receive bandwidth> Gbit/s
context-b -> context-a: <average aggregate receive bandwidth> Gbit/s
Duration: <seconds>s; parallel streams: <streams>
Endpoint strategy: <LoadBalancer or alternative>
```

`iperf3` reports throughput averaged across the requested test interval. If the user needs a longer-term average, run multiple independent trials in each direction and report the arithmetic mean and the individual results. Include retransmissions, failures, endpoint type, image, and relevant network-policy or egress constraints in the result.

## Safety And Cleanup

- Use explicit `--context` and `--namespace` on every `kubectl` command. Never change the user's current context.
- Do not use `--reverse` as a substitute for the second direction: it still runs a server in the same cluster and can obscure the intended network path. Swap the server and client contexts instead.
- Delete temporary pods and services even if the test fails after resource creation.
- Do not expose the server publicly beyond the test window. Prefer private load balancers or restricted security groups when the platform supports them.
- Avoid running this test during incident response or when high traffic could affect production workloads, unless the user explicitly accepts the impact.

## Verification

Before finalizing, verify that both direction labels correspond to the actual client and server contexts, each reported value came from `end.sum_received.bits_per_second`, and no temporary `iperf3` pods or services remain:

```bash
kubectl --context <context-a> -n <namespace> get pods,services -l run=<run-id>
kubectl --context <context-b> -n <namespace> get pods,services -l run=<run-id>
```
