"""Report construction, rendering and independent verification."""

from __future__ import annotations

from typing import Any

from . import fit as fit_module
from .model import Document

TOOL = "fretfit"
REPORT_VERSION = 1


def document_payload(doc: Document) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "instrument": doc.instrument,
        "scale_length_mm": doc.scale_length_mm,
        "saddle": doc.saddle_mode,
        "tolerance_cents": doc.tolerance_cents,
        "strings": [
            {
                "id": spec.id,
                "label": spec.label,
                "lateral_mm": spec.lateral_mm,
                "measurements": [
                    {"fret": point.fret, "cents": point.cents}
                    for point in spec.measurements
                ],
            }
            for spec in doc.strings
        ],
    }


def build(doc: Document, result: fit_module.FitResult) -> dict[str, Any]:
    strings = []
    for string_fit in result.string_fits:
        strings.append(
            {
                "id": string_fit.id,
                "label": string_fit.label,
                "lateral_mm": string_fit.lateral_mm,
                "nut_mm": round(string_fit.nut_mm, 6),
                "saddle_mm": round(string_fit.saddle_mm, 6),
                "max_residual_cents": round(string_fit.max_residual_cents, 6),
                "before_max_cents": round(string_fit.before_max_cents, 6),
                "single_point_saddle_mm": round(string_fit.single_point_saddle_mm, 6),
                "single_point_max_cents": round(string_fit.single_point_max_cents, 6),
                "points": [
                    {
                        "fret": point.fret,
                        "measured_cents": round(point.measured_cents, 6),
                        "after_cents": round(point.after_cents, 6),
                    }
                    for point in string_fit.points
                ],
            }
        )

    return {
        "tool": TOOL,
        "report_version": REPORT_VERSION,
        "input": document_payload(doc),
        "result": {
            "status": "within-tolerance" if result.within_tolerance else "out-of-tolerance",
            "mode": result.mode,
            "tolerance_cents": result.tolerance_cents,
            "converged": result.converged,
            "straight_saddle": (
                {
                    "offset_mm": round(float(result.straight_offset_mm), 6),
                    "slope_mm_per_mm": round(float(result.straight_slope), 6),
                }
                if result.mode == "straight"
                else None
            ),
            "summary": {
                "strings": len(result.string_fits),
                "worst_before_cents": round(result.worst_before, 6),
                "worst_after_cents": round(result.worst_after, 6),
                "worst_single_point_cents": round(result.worst_single_point, 6),
                "improvement_cents": round(result.worst_before - result.worst_after, 6),
            },
            "strings": strings,
        },
    }


def render(report: dict[str, Any]) -> str:
    result = report["result"]
    summary = result["summary"]
    lines = [
        f"fretfit: {report['input']['instrument']}",
        f"scale {report['input']['scale_length_mm']:.2f} mm  mode {result['mode']}  "
        f"tolerance {result['tolerance_cents']:.2f} cents",
        f"status: {result['status']}  worst before {summary['worst_before_cents']:.2f}  "
        f"worst after {summary['worst_after_cents']:.2f}  "
        f"(single-point rule: {summary['worst_single_point_cents']:.2f})",
        "",
    ]
    if result["straight_saddle"]:
        straight = result["straight_saddle"]
        lines.append(
            f"straight saddle: offset {straight['offset_mm']:+.3f} mm, "
            f"slope {straight['slope_mm_per_mm']:+.3f} mm per lateral mm"
        )
        lines.append("")

    header = f"{'string':<8}{'nut mm':>9}{'saddle mm':>11}{'before':>9}{'after':>8}"
    lines.append(header)
    lines.append("-" * len(header))
    for entry in result["strings"]:
        lines.append(
            f"{entry['id']:<8}{entry['nut_mm']:>+9.3f}{entry['saddle_mm']:>+11.3f}"
            f"{entry['before_max_cents']:>9.2f}{entry['max_residual_cents']:>8.2f}"
        )

    lines.append("")
    lines.append("per-fret residuals after compensation (cents)")
    for entry in result["strings"]:
        cells = " ".join(
            f"{point['fret']}:{point['after_cents']:+.2f}" for point in entry["points"]
        )
        lines.append(f"  {entry['id']:<8}{cells}")

    if result["mode"] == "straight":
        lines.append("")
        if result["status"] == "within-tolerance":
            lines.append("verdict: one straight saddle line meets the tolerance")
        else:
            lines.append(
                "verdict: a straight saddle cannot meet the tolerance; individual "
                "saddle positions are needed per the table above"
            )
    return "\n".join(lines)


def verify_report(payload: object) -> tuple[bool, list[str], dict[str, Any]]:
    """Recompute a report from its embedded input and list discrepancies."""
    problems: list[str] = []
    if not isinstance(payload, dict):
        return False, ["report: expected a JSON object"], {}
    if payload.get("tool") != TOOL:
        problems.append("report.tool: not a fretfit report")
    claimed = payload.get("result")
    if not isinstance(claimed, dict):
        return False, problems + ["report.result: missing"], {}

    from .model import InputError, parse

    try:
        doc = parse(payload.get("input"))
    except InputError as exc:
        return False, problems + [f"report.input: {exc}"], {}

    try:
        fresh = fit_module.fit(doc)
    except ValueError as exc:
        return False, problems + [f"recomputation failed: {exc}"], {}

    claimed_strings = claimed.get("strings")
    if not isinstance(claimed_strings, list) or len(claimed_strings) != len(fresh.string_fits):
        return False, problems + ["report.result.strings: does not match the input"], {}

    for entry, recomputed in zip(claimed_strings, fresh.string_fits):
        if not isinstance(entry, dict):
            problems.append("report.result.strings: expected objects")
            continue
        where = f"report.result.strings[{recomputed.id}]"
        if entry.get("id") != recomputed.id:
            problems.append(f"{where}: string order or id mismatch")
            continue
        for field, expected in (
            ("nut_mm", recomputed.nut_mm),
            ("saddle_mm", recomputed.saddle_mm),
            ("max_residual_cents", recomputed.max_residual_cents),
            ("single_point_max_cents", recomputed.single_point_max_cents),
        ):
            try:
                claimed_value = float(entry.get(field))
            except (TypeError, ValueError):
                problems.append(f"{where}.{field}: missing or not a number")
                continue
            if abs(claimed_value - expected) > 1e-4:
                problems.append(
                    f"{where}.{field}: claim {claimed_value:.6f} != recomputed {expected:.6f}"
                )

        claimed_points = entry.get("points")
        if not isinstance(claimed_points, list) or len(claimed_points) != len(recomputed.points):
            problems.append(f"{where}.points: does not match the measurements")
            continue
        for point_entry, point_fit in zip(claimed_points, recomputed.points):
            if not isinstance(point_entry, dict) or point_entry.get("fret") != point_fit.fret:
                problems.append(f"{where}.points: fret mismatch")
                continue
            try:
                claimed_after = float(point_entry.get("after_cents"))
            except (TypeError, ValueError):
                problems.append(f"{where}.points[{point_fit.fret}].after_cents: not a number")
                continue
            if abs(claimed_after - point_fit.after_cents) > 1e-4:
                problems.append(
                    f"{where}.points[{point_fit.fret}].after_cents: does not recompute"
                )

    expected_status = "within-tolerance" if fresh.within_tolerance else "out-of-tolerance"
    if claimed.get("status") != expected_status:
        problems.append(
            f"report.result.status: claim {claimed.get('status')!r} != recomputed {expected_status!r}"
        )
    summary = claimed.get("summary")
    if not isinstance(summary, dict):
        problems.append("report.result.summary: missing")
    else:
        for field, expected in (
            ("worst_after_cents", fresh.worst_after),
            ("worst_before_cents", fresh.worst_before),
            ("worst_single_point_cents", fresh.worst_single_point),
        ):
            try:
                claimed_value = float(summary.get(field))
            except (TypeError, ValueError):
                problems.append(f"report.result.summary.{field}: not a number")
                continue
            if abs(claimed_value - expected) > 1e-4:
                problems.append(f"report.result.summary.{field}: does not recompute")

    outcome = {
        "strings": len(fresh.string_fits),
        "status": expected_status,
        "worst_after_cents": round(fresh.worst_after, 6),
        "problems": problems,
        "ok": not problems,
    }
    return not problems, problems, outcome
