# Deployments

## Pipeline
Every merge to `main` builds an immutable container image tagged with the commit SHA. Images are promoted through
**staging → canary → production**; a build is never rebuilt between environments.

## Canary
Production deploys start with a canary receiving **5% of traffic for 20 minutes**. The canary is automatically
rolled back if the error rate exceeds the baseline by more than 1 percentage point or p95 latency rises by more than
25%.

## Deployment freeze
There is a deployment freeze from **18 December to 2 January** and on the last business day of each quarter.
Emergency fixes during a freeze need approval from the VP of Engineering and must have a rollback plan attached.

## Rollback
Rollback means redeploying the previous image tag with `deployctl rollback <service>`; it must complete within
10 minutes. Database migrations must be backward compatible for one release so that a rollback never requires a
down-migration.
