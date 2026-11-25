"""Geometry and compensation fitting.

The model
---------
A fret at nominal position ``x_k = S * (1 - 2^(-k/12))`` is fixed in the board.
Moving the nut toward the bridge by ``nut`` and the saddle away from the nut by
``saddle`` gives

    open speaking length  = S + saddle - nut
    speaking length at k  = S + saddle - x_k

so the geometric pitch error introduced by the offsets is

    dev_k = 1200 * log2( ((S + saddle - nut) / (S + saddle - x_k)) / 2^(k/12) )

``dev_k`` is zero at every fret when both offsets are zero. Measured sharpness
(``cents > 0``) is cancelled when ``dev_k`` is negative by roughly the same
amount, so a fit minimizes ``sum_k (cents_k + dev_k)^2``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .model import Document, StringSpec

OFFSET_MIN_MM = -6.0
OFFSET_MAX_MM = 30.0


@dataclass(frozen=True)
class PointFit:
    fret: int
    measured_cents: float
    after_cents: float


@dataclass(frozen=True)
class StringFit:
    id: str
    label: str
    lateral_mm: float
    nut_mm: float
    saddle_mm: float
    max_residual_cents: float
    before_max_cents: float
    single_point_saddle_mm: float
    single_point_max_cents: float
    points: tuple[PointFit, ...]


@dataclass(frozen=True)
class FitResult:
    mode: str
    tolerance_cents: float
    string_fits: tuple[StringFit, ...]
    straight_offset_mm: float | None
    straight_slope: float | None
    converged: bool

    @property
    def worst_after(self) -> float:
        return max((fit.max_residual_cents for fit in self.string_fits), default=0.0)

    @property
    def worst_before(self) -> float:
        return max((fit.before_max_cents for fit in self.string_fits), default=0.0)

    @property
    def worst_single_point(self) -> float:
        return max((fit.single_point_max_cents for fit in self.string_fits), default=0.0)

    @property
    def within_tolerance(self) -> bool:
        return self.worst_after <= self.tolerance_cents + 1e-9


def fret_position(scale_mm: float, fret: int) -> float:
    """Nominal distance from the nut to the fret, for an uncompensated board."""
    return scale_mm * (1.0 - 2.0 ** (-fret / 12.0))


def deviation_cents(scale_mm: float, fret: int, nut_mm: float, saddle_mm: float) -> float:
    """Geometric pitch error introduced by nut and saddle offsets, in cents."""
    position = fret_position(scale_mm, fret)
    open_length = scale_mm + saddle_mm - nut_mm
    fret_length = scale_mm + saddle_mm - position
    if open_length <= 1e-9 or fret_length <= 1e-9:
        raise ValueError("offsets put the saddle or nut behind a fret")
    ratio = open_length / fret_length
    return 1200.0 * math.log2(ratio / (2.0 ** (fret / 12.0)))


def _cost(scale_mm: float, points, nut_mm: float, saddle_mm: float) -> float:
    total = 0.0
    for point in points:
        residual = point.cents + deviation_cents(scale_mm, point.fret, nut_mm, saddle_mm)
        total += residual * residual
    return total


def _clamp(value: float) -> float:
    return min(OFFSET_MAX_MM, max(OFFSET_MIN_MM, value))


def fit_nut_saddle(scale_mm: float, points) -> tuple[float, float, bool]:
    """Least-squares nut and saddle offsets for one string (Gauss-Newton)."""
    nut, saddle = 0.0, 0.0
    best = _cost(scale_mm, points, nut, saddle)
    converged = False
    step = 1e-4

    for _ in range(80):
        jtj = [[0.0, 0.0], [0.0, 0.0]]
        jtr = [0.0, 0.0]
        for point in points:
            fret = point.fret
            residual = point.cents + deviation_cents(scale_mm, fret, nut, saddle)
            d_nut = (
                deviation_cents(scale_mm, fret, nut + step, saddle)
                - deviation_cents(scale_mm, fret, nut - step, saddle)
            ) / (2 * step)
            d_saddle = (
                deviation_cents(scale_mm, fret, nut, saddle + step)
                - deviation_cents(scale_mm, fret, nut, saddle - step)
            ) / (2 * step)
            jtj[0][0] += d_nut * d_nut
            jtj[0][1] += d_nut * d_saddle
            jtj[1][1] += d_saddle * d_saddle
            jtr[0] += d_nut * residual
            jtr[1] += d_saddle * residual

        det = jtj[0][0] * jtj[1][1] - jtj[0][1] * jtj[0][1]
        if abs(det) < 1e-18:
            break
        step_nut = (-jtj[1][1] * jtr[0] + jtj[0][1] * jtr[1]) / det
        step_saddle = (jtj[0][1] * jtr[0] - jtj[0][0] * jtr[1]) / det

        improved = False
        damping = 1.0
        for _ in range(30):
            candidate_nut = _clamp(nut + step_nut * damping)
            candidate_saddle = _clamp(saddle + step_saddle * damping)
            cost = _cost(scale_mm, points, candidate_nut, candidate_saddle)
            if cost < best - 1e-15:
                nut, saddle, best = candidate_nut, candidate_saddle, cost
                improved = True
                converged = True
                break
            damping *= 0.5
        if not improved:
            break
        if abs(step_nut) + abs(step_saddle) < 1e-10:
            break

    return nut, saddle, converged


def _fit_nut_only(scale_mm: float, points, saddle_mm: float) -> float:
    """Golden-section search over the nut offset with the saddle fixed."""
    low, high = OFFSET_MIN_MM, OFFSET_MAX_MM
    golden = (math.sqrt(5.0) - 1.0) / 2.0
    left = high - golden * (high - low)
    right = low + golden * (high - low)
    cost_left = _cost(scale_mm, points, left, saddle_mm)
    cost_right = _cost(scale_mm, points, right, saddle_mm)
    for _ in range(140):
        if cost_left < cost_right:
            high, right, cost_right = right, left, cost_left
            left = high - golden * (high - low)
            cost_left = _cost(scale_mm, points, left, saddle_mm)
        else:
            low, left, cost_left = left, right, cost_right
            right = low + golden * (high - low)
            cost_right = _cost(scale_mm, points, right, saddle_mm)
    return (low + high) / 2.0


def _fit_line(
    scale_mm: float,
    strings: tuple[StringSpec, ...],
    nuts: list[float],
    start: tuple[float, float],
) -> tuple[float, float, bool]:
    """Fit saddle offset = a + b * lateral across all strings (Gauss-Newton)."""
    a, b = start
    best = sum(
        _cost(scale_mm, spec.measurements, nuts[index], a + b * spec.lateral_mm)
        for index, spec in enumerate(strings)
    )
    converged = False
    step = 1e-4

    for _ in range(80):
        jtj = [[0.0, 0.0], [0.0, 0.0]]
        jtr = [0.0, 0.0]
        for index, spec in enumerate(strings):
            saddle = a + b * spec.lateral_mm
            for point in spec.measurements:
                fret = point.fret
                residual = point.cents + deviation_cents(scale_mm, fret, nuts[index], saddle)
                d_saddle = (
                    deviation_cents(scale_mm, fret, nuts[index], saddle + step)
                    - deviation_cents(scale_mm, fret, nuts[index], saddle - step)
                ) / (2 * step)
                jtj[0][0] += d_saddle * d_saddle
                jtj[0][1] += d_saddle * d_saddle * spec.lateral_mm
                jtj[1][1] += d_saddle * d_saddle * spec.lateral_mm * spec.lateral_mm
                jtr[0] += d_saddle * residual
                jtr[1] += d_saddle * residual * spec.lateral_mm
        det = jtj[0][0] * jtj[1][1] - jtj[0][1] * jtj[0][1]
        if abs(det) < 1e-18:
            break
        step_a = (-jtj[1][1] * jtr[0] + jtj[0][1] * jtr[1]) / det
        step_b = (jtj[0][1] * jtr[0] - jtj[0][0] * jtr[1]) / det
        improved = False
        damping = 1.0
        for _ in range(30):
            candidate_a = a + step_a * damping
            candidate_b = b + step_b * damping
            cost = sum(
                _cost(
                    scale_mm,
                    spec.measurements,
                    nuts[index],
                    candidate_a + candidate_b * spec.lateral_mm,
                )
                for index, spec in enumerate(strings)
            )
            if cost < best - 1e-15:
                a, b, best = candidate_a, candidate_b, cost
                improved = True
                converged = True
                break
            damping *= 0.5
        if not improved:
            break
        if abs(step_a) + abs(step_b) < 1e-12:
            break

    return a, b, converged


_EMPTY_START = (0.0, 0.0)


def _single_point_saddle(scale_mm: float, points) -> float:
    """Saddle offset from the 12th-fret error alone, the classic rule of thumb."""
    target_point = min(points, key=lambda point: abs(point.fret - 12))
    target = -target_point.cents
    position = fret_position(scale_mm, target_point.fret)
    low = position - scale_mm + 0.5
    high = 60.0

    def value(offset: float) -> float:
        return deviation_cents(scale_mm, target_point.fret, 0.0, offset)

    value_low, value_high = value(low), value(high)
    if target >= value_low:
        return low
    if target <= value_high:
        return high
    for _ in range(200):
        middle = (low + high) / 2.0
        if value(middle) > target:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def fit(doc: Document) -> FitResult:
    """Fit nut and saddle compensation for every string in the document."""
    scale = doc.scale_length_mm
    converged = True

    if doc.saddle_mode == "individual":
        nuts: list[float] = []
        saddles: list[float] = []
        for spec in doc.strings:
            nut, saddle, ok = fit_nut_saddle(scale, spec.measurements)
            nuts.append(nut)
            saddles.append(saddle)
            converged = converged and ok
        offset = slope = None
    else:
        offset, slope = 0.0, 0.0
        nuts = [0.0] * len(doc.strings)
        for _ in range(40):
            for index, spec in enumerate(doc.strings):
                saddle = offset + slope * spec.lateral_mm
                nuts[index] = _fit_nut_only(scale, spec.measurements, saddle)
            new_offset, new_slope, ok = _fit_line(scale, doc.strings, nuts, (offset, slope))
            converged = converged and ok
            shift = abs(new_offset - offset) + abs(new_slope - slope)
            offset, slope = new_offset, new_slope
            if shift < 1e-9:
                break
        saddles = [offset + slope * spec.lateral_mm for spec in doc.strings]

    fits: list[StringFit] = []
    for index, spec in enumerate(doc.strings):
        nut = nuts[index]
        saddle = saddles[index]
        points = tuple(
            PointFit(
                fret=point.fret,
                measured_cents=point.cents,
                after_cents=point.cents + deviation_cents(scale, point.fret, nut, saddle),
            )
            for point in spec.measurements
        )
        single = _single_point_saddle(scale, spec.measurements)
        single_max = max(
            abs(point.cents + deviation_cents(scale, point.fret, 0.0, single))
            for point in spec.measurements
        )
        fits.append(
            StringFit(
                id=spec.id,
                label=spec.label,
                lateral_mm=spec.lateral_mm,
                nut_mm=nut,
                saddle_mm=saddle,
                max_residual_cents=max(abs(point.after_cents) for point in points),
                before_max_cents=max(abs(point.cents) for point in spec.measurements),
                single_point_saddle_mm=single,
                single_point_max_cents=single_max,
                points=points,
            )
        )

    return FitResult(
        mode=doc.saddle_mode,
        tolerance_cents=doc.tolerance_cents,
        string_fits=tuple(fits),
        straight_offset_mm=offset if doc.saddle_mode == "straight" else None,
        straight_slope=slope if doc.saddle_mode == "straight" else None,
        converged=converged,
    )
