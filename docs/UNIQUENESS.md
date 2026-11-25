# Uniqueness investigation - fretfit

## Closest existing alternatives

1. **Liutaio Mottola, "Adjusting Bridge Saddle for Proper Intonation"**: a
   calculator converting one measured 12th-fret cents error into a saddle
   displacement.
2. **Liutaio Mottola, bridge saddle compensation calculator**: predicts
   compensation per string from gauge, action and instrument family.
3. **The Luthiers App bridge compensation calculator**: per-string setback
   estimate with an editable model.
4. **CMUSE intonation and saddle compensation calculators**: single-point
   conversions and presets, with action-based estimates.
5. **Gregory Byers' published method**: statistical fit of a canonical fret
   equation to a measured fret set, presented as a research method with sample
   values, not as a tool.
6. **JASA 2024, "Classical guitar intonation and compensation"**: least-squares
   selection of nut and saddle setbacks for a string set, published as a paper.

## Similarities

The geometry is the standard equal-tempered fret layout, and the goal - reduce
fretted sharpness by moving the nut and saddle - is the same. Any tool in this
space uses the same cents-to-length relationship.

## Meaningful differences

- The calculators convert **one** measurement (usually fret 12) into **one**
  offset. `fretfit` uses the whole measured table and fits nut and saddle
  jointly, so it can report what remains at every fret instead of assuming the
  rest follows.
- It quantifies the alternative: the same data run through the single-point
  rule, with its worst residual, so the user can see what the rule leaves on
  the table.
- Straight-saddle planning is a first-class constrained fit (offset plus angle
  across string positions), with a tolerance verdict and the implied per-string
  offsets when the line cannot work.
- Reports are verifiable: `verify` re-fits the embedded measurements.

## Unique mechanism

A two-parameter geometric deviation model fitted by damped Gauss-Newton per
string, plus an alternating fit for the straight-saddle case (golden-section
nut search inside a constrained two-parameter line fit), with residual,
rule-comparison and tolerance reporting.

## Why this deserves its own repository

Published methods describe the statistics; calculators implement the one-point
rule. A tool that ingests a table, fits both offsets, compares against the rule
and checks straight-saddle feasibility is a different capability, and small
shops can run it offline in CI or on a bench laptop.

## Remaining originality uncertainties

- Commercial fret-slotting and setup software may compute similar fits
  internally; no public documentation of this exact workflow was found.
- Byers' and the JASA work establish the underlying mathematics; this project
  claims the implementation and workflow, not the physics.
- The fit is only as good as the measurements: a user with a poor tuner will
  get a precise-looking answer from noisy input, which the residual table is
  meant to expose.
