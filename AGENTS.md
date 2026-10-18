# Project agent notes

## DSH ACL diagnostic reports

The `diagnose-windows-sandbox-acl` skill writes its recovery record, rollback
script, and JSONL report to the directory passed as `-Out`. Never point `-Out`
at this repository.

- Use a persistent user-level directory, for example
  `$env:LOCALAPPDATA\DSH\acl-reports`.
- `.dsh-acl-reports/` is gitignored only as a fallback; do not rely on it.
