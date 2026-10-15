# Data retention

## Customer data
Customer data is retained while the account is active. After an account is closed it is deleted within **90 days**,
except records we are legally required to keep.

## Logs
Application logs are retained for **30 days** in hot storage and **1 year** in cold storage. Logs must never contain
passwords, full card numbers or government ID numbers; log scrubbing runs at ingestion.

## Backups
Database backups are taken every 6 hours, retained for **35 days**, encrypted, and restored in a drill once per
quarter. A restore drill that fails is treated as a SEV2.

## Deletion requests
Data subject deletion requests must be completed within **30 days** and are tracked in the privacy queue.
