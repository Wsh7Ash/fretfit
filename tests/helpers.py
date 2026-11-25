"""Synthetic measurement documents with known compensation offsets."""

from __future__ import annotations

from fretfit.fit import deviation_cents

SCALE = 645.16
FRETS = (3, 5, 7, 9, 12, 15, 17)


def measurements_for(nut: float, saddle: float, scale: float = SCALE, frets=FRETS, bias: float = 0.0):
    return [
        {"fret": fret, "cents": round(-deviation_cents(scale, fret, nut, saddle) + bias, 6)}
        for fret in frets
    ]


def document(
    *,
    nut: float = -0.35,
    saddle: float = 2.4,
    scale: float = SCALE,
    mode: str = "individual",
    laterals: tuple[float, ...] = (0.0, 9.5, 19.0, 28.5, 38.0, 47.5),
    slope: float = 0.0,
    tolerance: float = 3.0,
    ids: tuple[str, ...] = ("E6", "A5", "D4", "G3", "B2", "E1"),
):
    strings = []
    for index, string_id in enumerate(ids):
        lateral = laterals[index % len(laterals)]
        string_saddle = saddle + slope * lateral
        strings.append(
            {
                "id": string_id,
                "label": string_id,
                "lateral_mm": lateral,
                "measurements": measurements_for(nut, string_saddle, scale=scale),
            }
        )
    return {
        "schema_version": 1,
        "instrument": "synthetic test instrument",
        "scale_length_mm": scale,
        "saddle": mode,
        "tolerance_cents": tolerance,
        "strings": strings,
    }
