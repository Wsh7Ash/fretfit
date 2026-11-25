"""Input schema for fretfit measurement documents."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MAX_FRET = 24
MIN_SCALE_MM = 100.0
MAX_SCALE_MM = 2000.0
DEFAULT_TOLERANCE_CENTS = 3.0
SADDLE_MODES = ("individual", "straight")


class InputError(ValueError):
    """Raised when a measurement document violates the schema."""


@dataclass(frozen=True)
class Measurement:
    fret: int
    cents: float


@dataclass(frozen=True)
class StringSpec:
    id: str
    label: str
    lateral_mm: float
    measurements: tuple[Measurement, ...]


@dataclass(frozen=True)
class Document:
    instrument: str
    scale_length_mm: float
    saddle_mode: str
    tolerance_cents: float
    strings: tuple[StringSpec, ...]


def _mapping(value: Any, where: str) -> dict:
    if not isinstance(value, dict):
        raise InputError(f"{where}: expected an object")
    return value


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InputError(f"{where}: expected a non-empty string")
    return value.strip()


def _number(value: Any, where: str, *, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InputError(f"{where}: expected a number")
    number = float(value)
    if not math.isfinite(number):
        raise InputError(f"{where}: expected a finite number")
    if minimum is not None and number < minimum:
        raise InputError(f"{where}: expected a number >= {minimum:g}")
    if maximum is not None and number > maximum:
        raise InputError(f"{where}: expected a number <= {maximum:g}")
    return number


def parse(document: Any) -> Document:
    """Validate a decoded measurement document."""
    doc = _mapping(document, "document")
    version = doc.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise InputError(
            f"document.schema_version: expected {SCHEMA_VERSION}, got {version!r}"
        )

    instrument = _text(doc.get("instrument", "unspecified instrument"), "document.instrument")
    scale = _number(
        doc.get("scale_length_mm"),
        "document.scale_length_mm",
        minimum=MIN_SCALE_MM,
        maximum=MAX_SCALE_MM,
    )
    mode = doc.get("saddle", "individual")
    if mode not in SADDLE_MODES:
        raise InputError(
            "document.saddle: expected 'individual' or 'straight'"
        )
    tolerance = _number(
        doc.get("tolerance_cents", DEFAULT_TOLERANCE_CENTS),
        "document.tolerance_cents",
        minimum=0.1,
        maximum=25.0,
    )

    raw_strings = doc.get("strings")
    if not isinstance(raw_strings, list) or not raw_strings:
        raise InputError("document.strings: expected a non-empty list")

    strings: list[StringSpec] = []
    seen: set[str] = set()
    for index, raw in enumerate(raw_strings):
        where = f"document.strings[{index}]"
        entry = _mapping(raw, where)
        string_id = _text(entry.get("id"), f"{where}.id")
        if string_id in seen:
            raise InputError(f"{where}.id: duplicate string id {string_id!r}")
        seen.add(string_id)
        label = _text(entry.get("label", string_id), f"{where}.label")
        lateral = _number(entry.get("lateral_mm", 0.0), f"{where}.lateral_mm", maximum=200.0, minimum=-200.0)

        raw_points = entry.get("measurements")
        if not isinstance(raw_points, list):
            raise InputError(f"{where}.measurements: expected a list")
        if len(raw_points) < 3:
            raise InputError(
                f"{where}.measurements: at least 3 frets are needed to separate nut and saddle effects"
            )
        measurements: list[Measurement] = []
        frets_seen: set[int] = set()
        for point_index, point in enumerate(raw_points):
            point_where = f"{where}.measurements[{point_index}]"
            point_map = _mapping(point, point_where)
            fret = point_map.get("fret")
            if isinstance(fret, bool) or not isinstance(fret, int) or not (1 <= fret <= MAX_FRET):
                raise InputError(f"{point_where}.fret: expected an integer from 1 to {MAX_FRET}")
            if fret in frets_seen:
                raise InputError(f"{point_where}.fret: duplicate fret {fret}")
            frets_seen.add(fret)
            cents = _number(point_map.get("cents"), f"{point_where}.cents", minimum=-200.0, maximum=200.0)
            measurements.append(Measurement(fret=fret, cents=cents))

        if mode == "straight" and "lateral_mm" not in entry:
            raise InputError(
                f"{where}.lateral_mm: required in straight-saddle mode so strings can share one saddle line"
            )
        measurements.sort(key=lambda item: item.fret)
        strings.append(
            StringSpec(
                id=string_id,
                label=label,
                lateral_mm=lateral,
                measurements=tuple(measurements),
            )
        )

    if mode == "straight":
        laterals = {spec.lateral_mm for spec in strings}
        if len(laterals) < 2:
            raise InputError(
                "document.strings: straight-saddle mode needs at least two distinct "
                "lateral_mm values, otherwise the saddle angle cannot be fitted"
            )

    return Document(
        instrument=instrument,
        scale_length_mm=scale,
        saddle_mode=mode,
        tolerance_cents=tolerance,
        strings=tuple(strings),
    )


def load(path: str | Path) -> Document:
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise InputError(f"{source}: {exc.strerror or exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputError(
            f"{source}: invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}"
        ) from exc
    return parse(payload)
