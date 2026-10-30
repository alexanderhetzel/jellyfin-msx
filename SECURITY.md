# Security policy

This project is a prototype; no production-supported release is published yet.
The maintained development branch is `main`. The preserved upstream `master`
branch is outside this independent implementation's maintenance scope.

Report vulnerabilities through
[GitHub private vulnerability reporting](https://github.com/alexanderhetzel/jellyfin-msx/security/advisories/new).
Do not include credentials or user data even in the initial report. Describe the
affected revision, expected/actual behavior and a reproduction using synthetic
accounts/data. Never post live tokens, pairing URLs, library details, screenshots
with private media, TLS keys or raw network captures in public issues.

No response-time or remediation SLA is promised. Normal bug reports belong in
repository issues. A discovered secret must be revoked/rotated before remediation;
deleting a Git commit does not make a leaked credential safe.

Current documented limitations include user-scoped Jellyfin tokens in native
media URLs, RAM-only portal sessions and incomplete expiry/restart revocation.
These are tracked as release work, not claims of production security. HTTPS,
random expiring capabilities, CSRF checks and disabled URL/access logging must
remain enabled. Never enable transcoding on the operator's Ultra deployment.
