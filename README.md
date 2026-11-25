# fretfit

Fit nut and saddle compensation from a measured fret table.

`fretfit` reads cents-off measurements at several frets per string, fits the nut
and saddle offsets that explain them, and prints what remains at every fret. It
also runs the classic 12th-fret rule on the same data so you can see what the
rule leaves behind, and it answers whether one straight saddle can meet a
tolerance across all strings.

## Why this exists

Saddle compensation is usually set from one measurement at fret 12: the note is
8 cents sharp, so move the saddle by a formula, done. But a setup that is perfect
at 12 can still be sharp at 3 and flat at 17, and a player notices. A whole
measured table contains enough information to separate nut effects from saddle
effects; most calculators throw that information away.

## Who it is for

- Luthiers and repair technicians doing setups
- Builders deciding between a straight, angled or individually compensated
  saddle
- Players who measure their own instruments with a strobe tuner
- Students learning why compensation is more than a 12th-fret rule

## What makes it different

- **Uses the whole table, not one fret.** Per string it fits two parameters
  (nut and saddle) against all measured frets and reports the residual curve.
- **Shows the rule of thumb's cost.** The same measurements are run through the
  single-point 12th-fret method and its worst residual is printed next to the
  joint fit's.
- **Treats a straight saddle as a constrained fit.** One line (offset plus
  angle across the bridge) with per-string nut offsets; the verdict says whether
  it meets the tolerance, and the table gives the individual positions when it
  does not.
- **Verifiable reports.** `verify` re-fits the embedded measurements and checks
  every parameter, residual and verdict.

## Features

1. Strict measurement schema with helpful errors.
2. Geometric nut/saddle deviation model for equal-tempered fret layout.
3. Per-string joint least-squares fit (damped Gauss-Newton).
4. Straight-saddle mode: shared offset and slope, per-string nuts, tolerance
   verdict.
5. Single-point rule comparison on the same data.
6. Text and JSON reports with the measurements embedded; `verify` recomputes.
7. Exit codes for scripting: within tolerance, outside, invalid input, no
   convergence.

## Requirements

Python 3.11 or newer. Standard library only.

## Quick start

```bash
python -m fretfit fit --input examples/six-string.json
```

```text
fretfit: steel-string 25.4 in scale (synthetic measurement set)
scale 645.16 mm  mode individual  tolerance 3.00 cents
status: within-tolerance  worst before 13.11  worst after 0.17  (single-point rule: 0.91)

string     nut mm  saddle mm   before   after
---------------------------------------------
E6         -0.429     +3.178    13.11    0.17
A5         -0.379     +2.778    11.48    0.17
D4         -0.329     +2.328     9.62    0.17
G3         -0.279     +1.678     6.88    0.17
B2         -0.229     +1.128     4.57    0.17
E1         -0.179     +0.828     3.36    0.17

per-fret residuals after compensation (cents)
  E6      3:+0.11 5:-0.14 7:+0.17 9:-0.17 12:+0.05 15:-0.17 17:+0.14
  ...
```

Straight saddle:

```bash
python -m fretfit fit --input examples/straight-saddle.json
python -m fretfit fit --input examples/straight-mismatch.json   # exits 1
```

Write and check a report:

```bash
python -m fretfit fit --input examples/six-string.json --json report.json
python -m fretfit verify report.json
```

## Input format

```json
{
  "schema_version": 1,
  "instrument": "shop instrument",
  "scale_length_mm": 645.16,
  "saddle": "individual",
  "tolerance_cents": 3.0,
  "strings": [
    {
      "id": "E6",
      "lateral_mm": 0.0,
      "measurements": [
        { "fret": 3, "cents": 2.1 },
        { "fret": 7, "cents": 4.8 },
        { "fret": 12, "cents": 8.2 }
      ]
    }
  ]
}
```

Positive `cents` means sharp. At least three frets per string are required to
separate nut from saddle effects. `lateral_mm` is the string's position across
the bridge; it is required in `"saddle": "straight"` mode and must take at least
two distinct values.

## Exit codes

| Command | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `fit` | meets the tolerance | valid fit, outside the tolerance | invalid input | solver did not converge |
| `verify` | reproduces | inconsistent | unreadable | - |

## Testing

```bash
python -m unittest discover -s tests
```

40 tests, including synthetic recovery (measurements generated from known
offsets come back within 0.02 mm), noise robustness, the straight-line case,
rule comparison, and tampered-report rejection.

## Limitations

- The model is geometric. Fretting stretch and bending stiffness are absorbed
  by the fit, not predicted from string properties, so the offsets are only as
  good as the measurement table.
- No confidence intervals; repeated measurements at the same frets are not
  supported yet.
- Offsets are clamped to [-6, 30] mm as a sanity bound.
- No fretboard layout or compensated fret-spacing output, and no microtonal
  support.
- A setup is a physical procedure: measure, move, re-measure. This tool gives
  the numbers, not the feel.

## Roadmap

- Weighted fits and intervals per fret
- Repeated-measurement support
- Per-string string-property priors
- Saddle-slot export

## License

MIT. See `LICENSE`.
