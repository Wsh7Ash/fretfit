# Usage - fretfit

## Measure

Tune the open string, then record the error in cents at several frets with a
strobe or a reliable app. Positive means the fretted note is **sharp**. Three
frets is the minimum; five to eight spread across the board works well.

```json
{
  "schema_version": 1,
  "instrument": "my instrument",
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
        { "fret": 12, "cents": 8.2 },
        { "fret": 17, "cents": 11.4 }
      ]
    }
  ]
}
```

`lateral_mm` is the string's position across the bridge; it is required in
straight-saddle mode and optional otherwise. Put the low string at 0 and
increase toward the treble side.

## Fit

```bash
python -m fretfit fit --input examples/six-string.json
python -m fretfit fit --input examples/six-string.json --json report.json
```

The report lists, per string, the fitted nut and saddle offsets, the worst
error before and after, and the worst error the single-point 12th-fret rule
would leave on the same measurements. A per-fret residual line follows.

## Straight saddle

```bash
python -m fretfit fit --input examples/straight-saddle.json
python -m fretfit fit --input examples/straight-mismatch.json
```

Straight mode fits one line (`offset + slope * lateral_mm`) shared by all
strings, with individual nut offsets. If the worst residual stays inside the
tolerance the verdict says the straight saddle works; otherwise the per-string
saddle column is the individual-saddle plan, and the exit code is 1.

## Verify

```bash
python -m fretfit verify report.json
```

`verify` re-parses the embedded measurements, re-fits, and compares every
parameter, residual and the status. It exits 0 with `verify: ok`, or lists
discrepancies and exits 1.

## Interpreting results

- A large nut offset with a small saddle offset means the instrument was
  uniformly sharp; a large saddle offset means sharpness grew with fret number.
- Residuals that stay above the tolerance across many frets mean the simple
  geometric model does not describe this setup: check the measurements, action,
  string condition and whether the frets themselves are worn.
- Offsets are relative to the current setup. Move the saddle by the printed
  amount from where it is now, then measure again.

## Exit codes

| Command | 0 | 1 | 2 | 3 |
|---|---|---|---|---|
| `fit` | meets tolerance | valid fit, outside tolerance | invalid input | solver did not converge |
| `verify` | reproduces | inconsistent | unreadable | - |
