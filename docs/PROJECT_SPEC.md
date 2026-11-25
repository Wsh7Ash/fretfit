# Project specification - fretfit

## 1. Vision

Turn a measured fret-by-fret pitch table into a defensible compensation plan:
how far the nut and saddle must move, what error remains, and whether one
straight saddle line can meet the tolerance.

## 2. Target audience

Luthiers, repair technicians, guitar builders, and players who measure their
own instruments and want more than a single-fret rule of thumb.

## 3. Problem statement

A fretted note is sharp because pressing the string stretches it. Compensation
moves the nut and saddle so fretted notes come back to pitch. The usual advice
uses only the 12th fret: measure the error, move the saddle by a formula, done.
That ignores the errors at every other fret, and it cannot say whether the
remaining error is acceptable or whether the nut also needs work.

## 4. Existing alternatives

- Liutaio Mottola's saddle-compensation calculator: single-point 12th-fret
  adjustment.
- Liutaio Mottola's bridge-compensation calculator: predicts compensation from
  gauge, action and instrument family.
- The Luthiers App bridge compensation calculator: per-string estimate from
  physical parameters.
- CMUSE intonation calculators: 12th-fret conversion from cents to saddle
  movement.
- Gregory Byers' published statistical method for fitting nut and saddle
  positions from measurements (prose/method, no tool).
- JASA 2024 paper on least-squares nut and saddle setbacks (research paper).

## 5. Competitive differentiation

`fretfit` fits both offsets jointly from the whole measured table, reports the
residual at every fret, compares the result with the classic single-point rule
on the same data, and answers the straight-saddle question as a constrained
fit (one line, unknown angle) with a tolerance verdict. The report is
recomputable by a verifier.

## 6. Core functionality

1. Validate a measurement document (scale, frets, cents, string layout).
2. Model the geometry of nut and saddle offsets.
3. Fit per-string nut and saddle offsets by damped Gauss-Newton.
4. Fit a shared straight saddle line (offset plus slope) with per-string nuts.
5. Compare with the 12th-fret single-point rule on the same measurements.
6. Emit text/JSON reports and verify them by recomputation.

## 7. Technical architecture

`model` (schema) -> `fit` (geometry, least squares, straight-line fit, rule
comparison) -> `report` (payload, rendering, verification) -> `cli`.

## 8. Main components

- `fretfit/model.py`: measurement schema and validation.
- `fretfit/fit.py`: deviation model, Gauss-Newton fits, single-point rule.
- `fretfit/report.py`: report assembly, ASCII rendering, verifier.
- `fretfit/cli.py`: `fit` and `verify` commands with exit codes.

## 9. Data flow

Measurements JSON -> validated `Document` -> per-string fits (or a straight-line
iteration) -> `FitResult` -> report with embedded input -> optional JSON ->
`verify` re-fits the embedded input and compares parameters, residuals and
status.

## 10. Dependencies

Python standard library only. `unittest` for tests. No network.

## 11. Security considerations

One local input file, one optional output file, no network, no subprocesses, no
secrets. Numeric inputs are bounded and finite-checked. No personal data is
required; the schema deliberately has no customer or instrument serial field.
See `SECURITY.md`.

## 12. User workflows

- Diagnose an instrument: measure cents at several frets per string, run `fit`,
  read the nut and saddle offsets and the residual table.
- Decide on a bridge: run straight mode; if the verdict is out of tolerance,
  the table already gives the individual saddle positions.
- Audit: a colleague re-runs `verify` on the JSON report.

## 13. Testing strategy

- Geometry: zero offsets give zero deviation, signs match the physics, the
  effect grows with fret number.
- Recovery: synthetic tables generated from known offsets are recovered within
  0.02 mm; noise shows up as bounded parameter drift.
- Straight saddle: a true line is recovered; independent offsets are correctly
  reported as unachievable.
- Rule comparison: the joint fit is never worse than the single-point rule on
  noisy data.
- CLI and verifier: exit codes, tamper rejection, ASCII output.

## 14. Definition of done

Tests pass, the demo gate passes, the shipped synthetic examples reproduce
their documented statuses, and the verifier rejects altered reports.

## 15. Known limitations

- Geometric model only: fretting stretch and bending stiffness are absorbed
  empirically by the fit, not predicted from string properties.
- At least three frets per string are required to separate nut and saddle
  effects; more frets and a real strobe tuner give better results.
- Offsets are clamped to [-6, 30] mm, which is a sanity bound, not a bridge
  design space.
- Straight-saddle mode needs at least two distinct string lateral positions.
- The tool outputs offsets in millimetres for the measured setup; it does not
  produce a fretboard layout or a compensated fret spacing.
- It is not a substitute for playing tests and a competent setup.

## 16. Future development opportunities

Weighted fits by interval importance, per-string string-property priors,
confidence intervals from repeated measurements, compensated fretboard design,
and export to a saddle-slot drilling plan.
