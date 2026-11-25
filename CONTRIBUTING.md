# Contributing

## Setup

```bash
python -m unittest discover -s tests
bash scripts/demo.sh
```

Python 3.11+, standard library only. Nothing to install.

## Guidelines

- Keep `fit.py` free of file and network access; geometry and numerics only.
- Changes to the model need a synthetic recovery test: generate measurements
  from known offsets and check they come back.
- Changes to the report need a verifier test, including a tampered report that
  must be rejected.
- Keep output ASCII-only.
- Do not present the tool as a substitute for measurement practice; residuals
  are only as good as the input table.

## Reporting a bug

Include the measurement document, the command, and what you expected versus
what you saw. For numerical issues, say which tuner and how the frets were
measured; a plausible but noisy table is more useful than a curated one.
