#!/usr/bin/env python3
"""Generate C++ coefficient tables from the authors' Figshare supplements."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import hashlib
import json


def decimal_literal(text: str) -> str:
    """Keep the supplied decimal digits; normalize only the exponent spelling."""
    if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?", text):
        raise ValueError(f"invalid decimal coefficient: {text!r}")
    mantissa, _, exponent = text.upper().partition("E")
    return mantissa + (f"e{int(exponent)}" if exponent and int(exponent) else "")


def read_tables(root: Path):
    manifest = json.loads((root.parent / "provenance.json").read_text())
    for name in ("coefficients.txt", "minimax.c", "constants.h"):
        if hashlib.sha256((root / name).read_bytes()).hexdigest() != manifest["files"]["supplied/" + name]:
            raise ValueError(f"unexpected input checksum: {name}")
    blocks = {}
    for line in (root / "coefficients.txt").read_text().splitlines():
        if not line.strip():
            continue
        heading = re.fullmatch(r"F(\d+) (numerator|denominator)", line)
        if heading:
            key = int(heading[1]), heading[2]
            blocks[key] = []
        else:
            blocks[key].append(decimal_literal(line.strip()))
    # The last entry under F0 numerator is the first denominator (paper, Table II).
    assert blocks[0, "numerator"][-1] == "4.59649054199579770e11"
    blocks[0, "denominator"].insert(0, blocks[0, "numerator"].pop())
    constants = dict(re.findall(r"\b([cd]\d+)\s*=\s*([+\-\d.Ee]+)", (root / "minimax.c").read_text()))
    region_b = [[decimal_literal(constants[f"{letter}{i}"]) for i in range(6)] for letter in "cd"]
    region_b[1].append("1.00000000000000000")  # monic denominator
    bounds = dict(re.findall(r"\b(x_[01])\s*=\s*([\d.]+)", (root / "constants.h").read_text()))
    return bounds, [region_b] + [(blocks[n, "numerator"], blocks[n, "denominator"]) for n in range(33)]


def array(name: str, values: list[str]) -> str:
    body = ",\n      ".join(values)
    return (
        f"  inline static constexpr std::array<double, {len(values)}> {name} = {{\n"
        f"      {body},\n  }};\n"
    )


def generate(input_path: Path) -> str:
    bounds, parsed = read_tables(input_path)
    output = [
        "// Generated from Vikhamar-Sandberg and Repisky's CC BY 4.0 supplements (see README.md).",
        "// The paper specifies 17 significant digits for correctly rounded doubles.",
        "#ifndef FAST_BOYS_BENCHMARK_VIKHAMAR_SANDBERG_REPISKY_COEFFICIENTS_H_",
        "#define FAST_BOYS_BENCHMARK_VIKHAMAR_SANDBERG_REPISKY_COEFFICIENTS_H_",
        "",
        "#include <array>",
        "#include <cstddef>",
        "",
        "namespace fast_boys::benchmark::vikhamar_sandberg_repisky::coefficients {",
        "",
        "// Appendix D, Eqs. (D1) and (D2), for epsilon_tol = 5e-14.",
        f"inline constexpr double kRegionAEnd = {bounds['x_0']};",
        f"inline constexpr double kRegionBEnd = {bounds['x_1']};",
        "",
        "template <std::size_t Order>",
        "struct RegionA;",
        "",
    ]

    region_b_numerator, region_b_denominator = parsed[0]
    output.extend([
        "struct RegionB {",
        array("numerator", region_b_numerator).rstrip(),
        array("denominator", region_b_denominator).rstrip(),
        "};",
        "",
    ])

    for order, (numerator, denominator) in enumerate(parsed[1:]):
        output.extend([
            "template <>",
            f"struct RegionA<{order}> {{",
            array("numerator", numerator).rstrip(),
            array("denominator", denominator).rstrip(),
            "};",
            "",
        ])

    output.extend([
        "}  // namespace fast_boys::benchmark::vikhamar_sandberg_repisky::coefficients",
        "",
        "#endif  // FAST_BOYS_BENCHMARK_VIKHAMAR_SANDBERG_REPISKY_COEFFICIENTS_H_",
        "",
    ])
    return "\n".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="third_party/vsr/supplied directory")
    parser.add_argument("output", type=Path, help="generated C++ header")
    arguments = parser.parse_args()
    arguments.output.write_text(generate(arguments.input), encoding="utf-8")


if __name__ == "__main__":
    main()
