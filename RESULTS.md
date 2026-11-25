# Observed results - fretfit

All figures below were produced on 2026-11-25 with Python 3.14.3 on Windows,
from this repository, with no network access.

## Test suite

```text
$ python -m unittest discover -s tests
Ran 40 tests in 3.551s
OK
```

The suite covers:

- geometry: zero offsets give zero deviation at every fret 1-24, the sign of
  nut and saddle effects matches the physics, and the effect grows with fret
  number;
- recovery: measurements generated from known offsets are recovered within
  0.02 mm with residuals below 1e-4 cents;
- noise: with +/-0.4 cents random noise the parameters stay within 0.25 mm;
- straight saddle: a true line is recovered, and independent per-string
  offsets are correctly reported as unachievable;
- rule comparison: on 12 seeded noisy instances the joint fit is never worse
  than the single-point rule;
- CLI and verifier: exit codes, tampering, ASCII output.

## Build

```text
$ python -m compileall -q fretfit
exit 0
```

## Demo gate

```text
$ bash scripts/demo.sh
ok: individual fit meets the tolerance
ok: reports the tolerance verdict
ok: shows the single-point comparison
ok: a true straight saddle meets the tolerance
ok: prints the straight-saddle verdict
ok: independent offsets fail a straight saddle
ok: explains that individual saddles are needed
ok: verifier accepts the fresh report
ok: verifier prints its verdict
ok: verifier rejects a tampered offset
ok: verifier explains the rejection
demo: all checks passed
```

## Individual-saddle example

`examples/six-string.json` is a synthetic 645.16 mm scale set built from known
per-string offsets (-0.45 to -0.20 mm nut, 3.20 to 0.85 mm saddle) plus a fixed
noise pattern of +/-0.2 cents, so the truth is known and the fit can be scored.

```text
status: within-tolerance  worst before 13.11  worst after 0.17
                                     (single-point rule: 0.91)

string     nut mm  saddle mm   before   after
E6         -0.429     +3.178    13.11    0.17
A5         -0.379     +2.778    11.48    0.17
D4         -0.329     +2.328     9.62    0.17
G3         -0.279     +1.678     6.88    0.17
B2         -0.229     +1.128     4.57    0.17
E1         -0.179     +0.828     3.36    0.17
```

The fit recovers the generating offsets within 0.006 mm. Residuals equal the
injected noise pattern, which is what a correct least-squares fit should do.

## Straight-saddle example

`examples/straight-saddle.json` is generated from one line: offset 1.400 mm,
slope 0.045 mm per mm of lateral position, per-string nut offsets as above.

```text
straight saddle: offset +1.378 mm, slope +0.045 mm per lateral mm
status: within-tolerance  worst before 15.75  worst after 0.17
```

Recovered offset is 0.022 mm from the generating value; slope matches to three
decimals. A straight saddle is therefore sufficient for this family of setups.

## Straight-saddle mismatch

`examples/straight-mismatch.json` forces alternating low/high individual saddle
offsets (1.0 and 6.5 mm) onto one straight saddle.

```text
status: out-of-tolerance  worst before 27.90  worst after 7.82
straight saddle: offset +2.529 mm, slope +0.047 mm per lateral mm
exit code 1
```

The tool does not pretend the line works: the worst residual is 7.82 cents
against a 3.00 cent tolerance, the verdict names individual saddles, and the
per-string saddle column is the individual plan.

## Not run

- A real instrument: all example tables are synthetic and labelled as such.
  Measurement practice (tuner quality, fretting pressure, string condition)
  dominates real-world accuracy and is out of scope for this repository.
- Comparison against a commercial setup or fret-slotting package.
- Any claim about perceived playability: cents are not the whole setup.
