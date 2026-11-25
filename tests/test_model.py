"""Validation tests for measurement documents."""

import json
import tempfile
import unittest
from pathlib import Path

from fretfit import model

from helpers import document


class ParseTests(unittest.TestCase):
    def test_individual_mode_defaults(self):
        doc = model.parse(document())
        self.assertEqual(doc.saddle_mode, "individual")
        self.assertEqual(doc.tolerance_cents, 3.0)
        self.assertEqual(len(doc.strings), 6)
        self.assertEqual(doc.strings[0].measurements[0].fret, 3)

    def test_measurements_are_sorted(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"] = [
            {"fret": 12, "cents": 1.0},
            {"fret": 3, "cents": 2.0},
            {"fret": 7, "cents": 3.0},
        ]
        doc = model.parse(payload)
        self.assertEqual([point.fret for point in doc.strings[0].measurements], [3, 7, 12])

    def test_requires_three_measurements(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"] = payload["strings"][0]["measurements"][:2]
        with self.assertRaises(model.InputError) as ctx:
            model.parse(payload)
        self.assertIn("at least 3 frets", str(ctx.exception))

    def test_duplicate_fret_rejected(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"] = [
            {"fret": 5, "cents": 1},
            {"fret": 5, "cents": 2},
            {"fret": 7, "cents": 3},
        ]
        with self.assertRaises(model.InputError) as ctx:
            model.parse(payload)
        self.assertIn("duplicate fret", str(ctx.exception))

    def test_fret_bounds(self):
        for fret in (0, -1, 25):
            with self.subTest(fret=fret):
                payload = document()
                payload["strings"] = payload["strings"][:1]
                payload["strings"][0]["measurements"][0]["fret"] = fret
                with self.assertRaises(model.InputError):
                    model.parse(payload)

    def test_scale_bounds(self):
        for scale in (50.0, 2500.0):
            with self.subTest(scale=scale):
                payload = document()
                payload["scale_length_mm"] = scale
                with self.assertRaises(model.InputError):
                    model.parse(payload)

    def test_cents_bounds(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"][0]["cents"] = 400
        with self.assertRaises(model.InputError):
            model.parse(payload)

    def test_unknown_saddle_mode(self):
        payload = document()
        payload["saddle"] = "floating"
        with self.assertRaises(model.InputError) as ctx:
            model.parse(payload)
        self.assertIn("saddle", str(ctx.exception))

    def test_straight_mode_requires_lateral(self):
        payload = document(mode="straight", slope=0.5)
        del payload["strings"][0]["lateral_mm"]
        with self.assertRaises(model.InputError) as ctx:
            model.parse(payload)
        self.assertIn("lateral_mm", str(ctx.exception))

    def test_straight_mode_requires_distinct_laterals(self):
        payload = document(mode="straight", slope=0.5)
        for entry in payload["strings"]:
            entry["lateral_mm"] = 10.0
        with self.assertRaises(model.InputError) as ctx:
            model.parse(payload)
        self.assertIn("distinct", str(ctx.exception))

    def test_duplicate_string_id(self):
        payload = document()
        payload["strings"][1]["id"] = payload["strings"][0]["id"]
        with self.assertRaises(model.InputError):
            model.parse(payload)

    def test_empty_strings_rejected(self):
        payload = document()
        payload["strings"] = []
        with self.assertRaises(model.InputError):
            model.parse(payload)

    def test_unsupported_schema_version(self):
        payload = document()
        payload["schema_version"] = 9
        with self.assertRaises(model.InputError):
            model.parse(payload)

    def test_load_reads_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "measure.json"
            path.write_text(json.dumps(document()), encoding="utf-8")
            self.assertEqual(model.load(path).instrument, "synthetic test instrument")

    def test_load_reports_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "measure.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(model.InputError):
                model.load(path)
        with self.assertRaises(model.InputError):
            model.load("missing-measurement-file.json")


if __name__ == "__main__":
    unittest.main()
