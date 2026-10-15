# Incident response

## Severity levels
- **SEV1**: customer-facing outage or data loss affecting more than 10% of active customers, or any security breach.
- **SEV2**: major feature degraded for many customers, or an outage of an internal system that blocks releases.
- **SEV3**: minor degradation with a workaround.

## Roles
Every SEV1 and SEV2 has an **Incident Commander (IC)**, a **Communications Lead** and a **Scribe**. The IC
coordinates and makes decisions but does not debug. The Communications Lead posts customer status updates every
**30 minutes** for SEV1 and every 60 minutes for SEV2.

## Declaring an incident
Anyone can declare an incident with `/incident declare` in Slack. When in doubt, declare: downgrading later is free,
while declaring late is the most common cause of extended outages.

## Postmortems
A blameless postmortem is required for every SEV1 and SEV2 and must be published within **5 business days**.
Postmortems must include a timeline, contributing factors, and action items, each with an owner and a due date.
Action items from SEV1 postmortems are tracked in the weekly reliability review until closed.
