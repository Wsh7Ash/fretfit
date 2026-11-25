# Architecture - fretfit

```text
measurements JSON
    |
    v
model.parse  -- validation, normalization, dataclasses
    |
    v
fit.fit
    |-- individual mode:  per string, damped Gauss-Newton over (nut, saddle)
    |-- straight mode:    alternate
    |                       golden-section nut per string (saddle fixed)
    |                       Gauss-Newton over (offset, slope) across strings
    v
FitResult (per-string parameters, residuals, rule comparison, verdict)
    |
    v
report.build -- payload with embedded input
    |-- report.render (ASCII table + per-fret residuals)
    |-- cli writes JSON
            |
            v
      report.verify_report -- re-parse, re-fit, compare parameters and claims
```

## Geometry

With nominal scale `S`, fret `k` sits at `x_k = S (1 - 2^(-k/12))`. Nut offset
`n` (positive toward the bridge) and saddle offset `s` (positive away from the
nut) give open length `S + s - n` and fret length `S + s - x_k`. The geometric
pitch error is

```text
dev_k = 1200 log2( ((S + s - n) / (S + s - x_k)) / 2^(k/12) )
```

which is zero at every fret when `n = s = 0`. A fit minimizes
`sum_k (cents_k + dev_k)^2`.

## Numerical choices

- Analytic derivatives were avoided in favour of central differences
  (`h = 1e-4 mm`) because the residual is smooth and the parameter count is
  two; the Jacobian is exact enough for double precision convergence.
- Steps are damped (halved up to 30 times) and clipped to the offset box, so a
  bad starting region cannot overflow the model.
- The straight-saddle case alternates two small convex problems; 40 outer
  iterations with a 1e-9 change threshold is far more than convergence needs on
  real data.

## Determinism

No randomness, no iteration over sets or dictionaries in a numerically
meaningful order. Identical inputs give bit-identical reports.
