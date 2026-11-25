"""Geometry and fitting tests, including synthetic recovery."""

import random
import unittest

from fretfit import fit as fit_module
from fretfit import model

from helpers import SCALE, document, measurements_for


class GeometryTests(unittest.TestCase):
    def test_zero_offsets_have_zero_deviation(self):
        for fret in range(1, 25):
            with self.subTest(fret=fret):
                self.assertAlmostEqual(fit_module.deviation_cents(SCALE, fret, 0.0, 0.0), 0.0, places=9)

    def test_saddle_setback_flattens(self):
        for fret in (3, 7, 12, 17):
            with self.subTest(fret=fret):
                self.assertLess(fit_module.deviation_cents(SCALE, fret, 0.0, 2.0), 0.0)

    def test_nut_set_forward_flattens(self):
        for fret in (3, 7, 12, 17):
            with self.subTest(fret=fret):
                self.assertLess(fit_module.deviation_cents(SCALE, fret, 0.5, 0.0), 0.0)

    def test_compensation_effect_grows_with_fret(self):
        first = abs(fit_module.deviation_cents(SCALE, 2, 0.0, 2.0))
        last = abs(fit_module.deviation_cents(SCALE, 20, 0.0, 2.0))
        self.assertGreater(last, first)


class RecoveryTests(unittest.TestCase):
    def test_recovers_individual_offsets_exactly(self):
        doc = model.parse(document(nut=-0.42, saddle=2.65))
        result = fit_module.fit(doc)
        self.assertTrue(result.converged)
        for string_fit in result.string_fits:
            self.assertAlmostEqual(string_fit.nut_mm, -0.42, delta=0.02)
            self.assertAlmostEqual(string_fit.saddle_mm, 2.65, delta=0.02)
            self.assertLess(string_fit.max_residual_cents, 1e-4)
        self.assertTrue(result.within_tolerance)

    def test_constant_bias_is_absorbed_by_nut_offset(self):
        # A uniform sharpness across all frets is what a nut set-forward
        # corrects, so the two-parameter model should explain it almost fully.
        payload = document(nut=-0.42, saddle=2.65)
        for entry in payload["strings"]:
            for point in entry["measurements"]:
                point["cents"] = round(point["cents"] + 1.5, 6)
        result = fit_module.fit(model.parse(payload))
        self.assertLess(result.worst_after, 0.05)
        self.assertGreater(result.string_fits[0].nut_mm, -0.42)

    def test_recovers_from_measurement_noise(self):
        payload = document(nut=-0.2, saddle=2.0)
        rng = random.Random(4)
        for entry in payload["strings"]:
            for point in entry["measurements"]:
                point["cents"] = round(point["cents"] + rng.uniform(-0.4, 0.4), 6)
        result = fit_module.fit(model.parse(payload))
        for string_fit in result.string_fits:
            self.assertAlmostEqual(string_fit.nut_mm, -0.2, delta=0.25)
            self.assertAlmostEqual(string_fit.saddle_mm, 2.0, delta=0.25)

    def test_straight_saddle_recovers_line(self):
        payload = document(mode="straight", nut=-0.3, saddle=1.8, slope=0.6)
        result = fit_module.fit(model.parse(payload))
        self.assertIsNotNone(result.straight_offset_mm)
        self.assertAlmostEqual(result.straight_offset_mm, 1.8, delta=0.05)
        self.assertAlmostEqual(result.straight_slope, 0.6, delta=0.02)
        self.assertTrue(result.within_tolerance)

    def test_straight_saddle_cannot_fit_independent_offsets(self):
        payload = document(mode="straight", nut=-0.3, saddle=2.0)
        # Give each string a different saddle offset that no line can follow.
        offsets = [2.0, 5.5, 1.0, 6.5, 0.5, 7.0]
        for entry, offset in zip(payload["strings"], offsets):
            entry["measurements"] = measurements_for(-0.3, offset)
        result = fit_module.fit(model.parse(payload))
        self.assertFalse(result.within_tolerance)

    def test_individual_beats_single_point_rule(self):
        rng = random.Random(11)
        for case in range(12):
            nut = rng.uniform(-1.2, 0.4)
            saddle = rng.uniform(0.5, 4.0)
            payload = document(nut=nut, saddle=saddle)
            for entry in payload["strings"]:
                for point in entry["measurements"]:
                    point["cents"] = round(point["cents"] + rng.uniform(-0.8, 0.8), 6)
            result = fit_module.fit(model.parse(payload))
            with self.subTest(case=case):
                self.assertLessEqual(result.worst_after, result.worst_single_point + 1e-6)

    def test_flags_out_of_tolerance_measurements(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"] = [
            {"fret": 3, "cents": -15.0},
            {"fret": 7, "cents": 15.0},
            {"fret": 12, "cents": -15.0},
            {"fret": 17, "cents": 15.0},
        ]
        result = fit_module.fit(model.parse(payload))
        self.assertFalse(result.within_tolerance)
        self.assertGreater(result.worst_after, 3.0)

    def test_deterministic(self):
        doc = model.parse(document(nut=-0.5, saddle=3.1))
        first = fit_module.fit(doc)
        second = fit_module.fit(doc)
        self.assertEqual(first.worst_after, second.worst_after)
        self.assertEqual(
            [fit.nut_mm for fit in first.string_fits],
            [fit.nut_mm for fit in second.string_fits],
        )

    def test_extreme_data_stays_finite(self):
        payload = document()
        payload["strings"] = payload["strings"][:1]
        payload["strings"][0]["measurements"] = [
            {"fret": 2, "cents": 150.0},
            {"fret": 9, "cents": 120.0},
            {"fret": 18, "cents": 100.0},
        ]
        result = fit_module.fit(model.parse(payload))
        for string_fit in result.string_fits:
            self.assertGreaterEqual(string_fit.nut_mm, fit_module.OFFSET_MIN_MM - 1e-9)
            self.assertLessEqual(string_fit.nut_mm, fit_module.OFFSET_MAX_MM + 1e-9)
            self.assertGreaterEqual(string_fit.saddle_mm, fit_module.OFFSET_MIN_MM - 1e-9)
            self.assertLessEqual(string_fit.saddle_mm, fit_module.OFFSET_MAX_MM + 1e-9)
            self.assertTrue(string_fit.max_residual_cents == string_fit.max_residual_cents)


if __name__ == "__main__":
    unittest.main()
