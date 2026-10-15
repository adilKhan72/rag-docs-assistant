# Security practices

## Secrets
Secrets live in Vault and are injected at runtime. A secret committed to a repository is treated as compromised:
it must be **rotated within 4 hours**, even if the commit was reverted, and the incident logged as SEV2.

## Access
Production access is granted just-in-time through `accessctl` for a maximum of **8 hours** and requires a ticket
reference. Standing production access is not allowed for anyone, including administrators.

## Dependencies
Dependency updates are opened automatically. Critical vulnerabilities (CVSS 9.0 or above) must be patched within
**7 days**, high severity within 30 days.

## Laptops
Laptops must use full-disk encryption and lock after 5 minutes of inactivity. Lost devices must be reported to
`security@northwind.example` within one hour.
