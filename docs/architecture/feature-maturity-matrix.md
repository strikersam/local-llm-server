# Feature maturity / support matrix

## Stable core

- proxy endpoints
- auth
- routing + model aliasing
- key management
- observability + cost metrics
- direct chat
- validated runtime execution

## Beta

- built-in async direct-chat agent jobs
- runtime readiness diagnostics
- per-job progress polling

## Experimental

- OpenHands runtime
- optional sidecar runtimes not validated on the current host
- any feature that depends on binaries or services not present in runtime preflight

Rule: unstable integrations should fail in preflight or stay behind explicit runtime selection rather than failing late during execution.
