# Service level objectives

## Targets
The public API has an availability SLO of **99.9%** per rolling 30 days, which allows about 43 minutes of downtime.
The checkout service targets **99.95%**. Latency SLO for the public API: p99 under 800 ms.

## Error budgets
When a service has burned more than **50%** of its monthly error budget, feature releases slow down and reliability
work is prioritised. When the budget is exhausted, only fixes and security patches may ship until it recovers.

## Alerting
Alerts are based on burn rate, not raw thresholds: a fast-burn alert fires when the budget would be exhausted within
two days, and pages; a slow-burn alert fires when it would be exhausted within ten days, and creates a ticket.
