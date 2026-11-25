"""Command line interface.

Exit codes
----------
fit:    0 compensation meets the tolerance
        1 a valid fit, but the worst residual exceeds the tolerance
        2 invalid input or usage
        3 the solver did not converge
verify: 0 report reproduces from its embedded input
        1 report is inconsistent
        2 report cannot be read or parsed
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, fit as fit_module, model, report as report_module

EXIT_OK = 0
EXIT_OUT_OF_TOLERANCE = 1
EXIT_INPUT = 2
EXIT_NOT_CONVERGED = 3


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fretfit",
        description="Fit nut and saddle compensation from measured cents per fret.",
    )
    parser.add_argument("--version", action="version", version=f"fretfit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    fit_command = sub.add_parser("fit", help="fit compensation and print the table")
    fit_command.add_argument("--input", required=True, help="measurement JSON document")
    fit_command.add_argument("--json", dest="json_path", help="also write the full report as JSON")
    fit_command.add_argument("--quiet", action="store_true", help="suppress the text table")

    verify_command = sub.add_parser("verify", help="recompute a JSON report")
    verify_command.add_argument("report", help="report JSON produced by the fit command")
    verify_command.add_argument("--quiet", action="store_true", help="suppress the summary")
    return parser


def _fit(args: argparse.Namespace) -> int:
    try:
        doc = model.load(args.input)
    except model.InputError as exc:
        print(f"fretfit: {exc}", file=sys.stderr)
        return EXIT_INPUT

    try:
        result = fit_module.fit(doc)
    except ValueError as exc:
        print(f"fretfit: fit failed: {exc}", file=sys.stderr)
        return EXIT_NOT_CONVERGED

    payload = report_module.build(doc, result)

    if not args.quiet:
        print(report_module.render(payload))

    if args.json_path:
        try:
            Path(args.json_path).write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            print(
                f"fretfit: cannot write {args.json_path}: {exc.strerror or exc}",
                file=sys.stderr,
            )
            return EXIT_INPUT

    if not result.converged and result.worst_after > result.tolerance_cents:
        return EXIT_NOT_CONVERGED
    if result.within_tolerance:
        return EXIT_OK
    return EXIT_OUT_OF_TOLERANCE


def _verify(args: argparse.Namespace) -> int:
    path = Path(args.report)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"fretfit: cannot read {path}: {exc.strerror or exc}", file=sys.stderr)
        return EXIT_INPUT
    except json.JSONDecodeError as exc:
        print(f"fretfit: {path}: invalid JSON: {exc.msg}", file=sys.stderr)
        return EXIT_INPUT

    ok, problems, summary = report_module.verify_report(payload)
    if not args.quiet:
        if ok:
            print(
                f"verify: ok ({summary.get('strings')} strings, "
                f"{summary.get('status')}, worst {summary.get('worst_after_cents')} cents)"
            )
        else:
            print("verify: FAILED")
            for problem in problems:
                print(f"  - {problem}")
    return EXIT_OK if ok else EXIT_OUT_OF_TOLERANCE


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "fit":
        return _fit(args)
    if args.command == "verify":
        return _verify(args)
    parser.error("unknown command")
    return EXIT_INPUT
