# On-call rotation

Northwind Engineering runs a follow-the-sun on-call rotation across three regions: Islamabad, Lisbon and Austin.

## Shifts and handover
Each region covers an 8-hour primary shift. Handover happens in the `#oncall-handover` channel using the
handover template, and the outgoing engineer must list every open incident and any alert silenced in the last shift.
A shift is not considered handed over until the incoming engineer acknowledges in the thread.

## Paging policy
PagerDuty pages the primary first. If the page is not acknowledged within **5 minutes**, it escalates to the
secondary; after **15 minutes** it escalates to the engineering manager on call. Only SEV1 and SEV2 incidents page
outside working hours; SEV3 creates a ticket for the next business day.

## Compensation
Engineers receive an on-call stipend of **USD 150 per week** on rotation, plus time off in lieu: every page answered
between 22:00 and 06:00 local time earns two hours of TOIL, which must be used within 60 days.

## Rotation size
A rotation needs at least six engineers so nobody is primary more than one week in six. Teams smaller than six
must share a rotation with a sibling team.
