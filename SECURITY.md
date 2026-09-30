# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities privately through
[GitHub Security Advisories](https://github.com/iggym/surfacelock/security/advisories/new).
Do not open a public issue; if you cannot use advisories, contact a maintainer directly.

Please include: a description, a minimal reproduction, the version affected,
and any suggested remediation. We aim to acknowledge within 3 working days and
to ship a fix or a documented mitigation within 30 days.

## Supported versions

| Version | Supported |
|---|---|
| 0.1.x | ✅ |

During 0.x, only the latest minor receives security fixes.

## Design commitments relevant to security

- **No network calls.** The scanner never contacts a provider API. Everything
  it knows comes from the bundled registry and your repository.
- **No telemetry.** Nothing is phoned home, ever.
- **Secrets are never recorded.** The MCP scanner stores environment variable
  *names* and header *names* only. Values are hashed out of the config digest
  and never written to `surface.lock`, `scan --json`, or any output. A test in
  `tests/test_scanners.py` asserts this.
- **No code execution.** Scanned files are parsed, never imported or executed.
- **Read-only by default.** Only `init`, `update` and `pin` write, and `pin`
  rewrites source files only after an explicit confirmation prompt.

## Threat model notes

`surfacelock` reads untrusted repositories. The scanner is written to be
tolerant: it must never raise on syntax it does not understand, and it skips
files above 2 MB and binary files. A malformed file should degrade to fewer
findings, never to a crash or to code execution.

If you find an input that causes a crash, an unbounded memory allocation, or
any form of execution, that is a security bug — please report it.
