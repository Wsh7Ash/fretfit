# Security policy

## Scope

`fretfit` is an offline command-line tool. It reads one measurement JSON
document and optionally writes one JSON report. It has no network access, no
subprocesses, no credential handling and no executable deserialization.

## Supported versions

| Version | Supported |
|---|---|
| 1.x | yes |

## Design choices that limit risk

- `json.loads` only; no `eval`, `exec` or `pickle`.
- Every number is type-checked, finite-checked and bounded before it reaches
  the solver.
- Verification re-computes from the embedded input rather than trusting the
  report's claims.
- Output is written only to the path given on the command line, and only after
  a successful fit.

## Reporting a vulnerability

Open a private security advisory on the repository or contact the maintainer
listed in the repository profile. Include the input document and the command.
Do not include customer names or unpublished instrument details; synthetic
numbers are enough.
