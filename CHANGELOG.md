# Changelog

## 1.0.0 - 2026-11-25

- Initial release.
- Measurement schema with per-string frets, cents and bridge lateral position.
- Joint nut and saddle least-squares fit per string (damped Gauss-Newton).
- Straight-saddle mode: shared offset and slope with per-string nut offsets and
  a tolerance verdict.
- Single-point 12th-fret comparison shown alongside the joint fit.
- Verifiable JSON reports with embedded measurements.
- 40 automated tests including synthetic recovery and noise robustness.
