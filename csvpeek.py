#!/usr/bin/env python3
"""csvpeek -- peek into CSV files straight from the terminal.

Zero-dependency alternative to opening a spreadsheet just to check what is
inside a CSV: structure overview, head rows and quick statistics.

    csvpeek info data.csv
    csvpeek head data.csv -n 5
    csvpeek stats data.csv --cols price,qty

Encoding and delimiter are auto-detected (utf-8-sig / utf-8 / gbk / latin-1,
`,` `;` TAB `|`), which makes it friendly for files exported by Excel on
Chinese Windows. Both can be forced with --encoding / --delimiter.

Licensed under the MIT License.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

__version__ = "0.1.0"

ENCODING_CANDIDATES = ("utf-8-sig", "utf-8", "gbk", "latin-1")
DELIMITER_CANDIDATES = ",;\t|"
MAX_CELL_WIDTH = 28
TOP_VALUES = 3


# ---- loading -----------------------------------------------------------
def load_rows(path, encoding=None, delimiter=None):
    """Read a CSV file, auto-detecting encoding and delimiter.

    Returns (rows, used_encoding, used_delimiter) where rows is a list of
    dicts keyed by the header names.
    """
    data = Path(path).read_bytes()
    encodings = (encoding,) if encoding else ENCODING_CANDIDATES
    last_error = None
    for enc in encodings:
        try:
            text = data.decode(enc)
        except (UnicodeDecodeError, LookupError) as exc:
            last_error = exc
            continue
        if delimiter:
            used_delim = delimiter
        else:
            try:
                used_delim = csv.Sniffer().sniff(text[:4096], DELIMITER_CANDIDATES).delimiter
            except csv.Error:
                used_delim = ","
        rows = list(csv.DictReader(text.splitlines(), delimiter=used_delim))
        for row in rows:
            if None in row:  # rows with more fields than the header
                row["__extra__"] = row.pop(None)
        return rows, enc, used_delim
    raise ValueError(f"cannot decode {path}: {last_error}")


# ---- profiling ---------------------------------------------------------
def _as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def profile_column(values):
    """Classify non-missing values of a column: int / float / text / empty."""
    sample = [v for v in values if v not in (None, "")]
    if not sample:
        return "empty"
    numbers = [_as_number(v) for v in sample[:500]]
    if all(n is not None for n in numbers):
        looks_int = all(
            float(n).is_integer() and "." not in str(v) and "e" not in str(v).lower()
            for n, v in zip(numbers, sample[:500])
        )
        return "int" if looks_int else "float"
    return "text"


def profile_rows(rows):
    """Per-column profile: type, missing count, plus range or top values."""
    if not rows:
        return {}
    columns = {}
    for name in rows[0].keys():
        values = [row.get(name) for row in rows]
        kind = profile_column(values)
        non_missing = [v for v in values if v not in (None, "")]
        info = {"type": kind, "missing": len(values) - len(non_missing)}
        if kind in ("int", "float"):
            nums = [float(v) for v in non_missing]
            info["min"] = min(nums) if nums else None
            info["max"] = max(nums) if nums else None
        elif kind == "text":
            counts = {}
            for v in non_missing:
                counts[v] = counts.get(v, 0) + 1
            info["distinct"] = len(counts)
            info["top"] = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:TOP_VALUES]
        columns[name] = info
    return columns


# ---- payload builders --------------------------------------------------
def build_info_payload(rows, encoding, delimiter):
    return {
        "rows": len(rows),
        "columns": len(rows[0]) if rows else 0,
        "encoding": encoding,
        "delimiter": delimiter,
        "profile": profile_rows(rows),
    }


def build_head_payload(rows, n):
    names = list(rows[0].keys()) if rows else []
    return {
        "total": len(rows),
        "shown": min(n, len(rows)),
        "columns": names,
        "rows": [[str(row.get(name, "") if row.get(name) is not None else "")
                  for name in names] for row in rows[:n]],
    }


def build_stats_payload(rows, cols=None):
    profiles = profile_rows(rows)
    if cols:
        wanted = [c.strip() for c in cols.split(",") if c.strip()]
        unknown = [c for c in wanted if c not in profiles]
        if unknown:
            raise KeyError("unknown column(s): " + ", ".join(unknown))
        profiles = {c: profiles[c] for c in wanted}
    result = {}
    for name, info in profiles.items():
        non_missing = [row.get(name) for row in rows
                       if row.get(name) not in (None, "")]
        entry = {"type": info["type"], "n": len(non_missing), "missing": info["missing"]}
        if info["type"] in ("int", "float") and non_missing:
            nums = [float(v) for v in non_missing]
            entry.update({
                "mean": _sig(statistics.mean(nums)),
                "stdev": _sig(statistics.stdev(nums)) if len(nums) > 1 else None,
                "min": _sig(min(nums)),
                "median": _sig(statistics.median(nums)),
                "max": _sig(max(nums)),
            })
        else:
            entry["top"] = [list(pair) for pair in info.get("top", [])]
        result[name] = entry
    return {"columns": result}


def _sig(x, digits=6):
    return float(f"{x:.{digits}g}")


# ---- rendering ---------------------------------------------------------
def _cell(value, max_width=MAX_CELL_WIDTH):
    text = str(value)
    if len(text) > max_width:
        return text[: max_width - 1] + "…"
    return text


def render_table(header, rows):
    widths = [len(_cell(h)) for h in header]
    grid = [[_cell(c) for c in row] for row in rows]
    for row in grid:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    lines = [" | ".join(h.ljust(widths[i]) for i, h in enumerate(header)),
             "-+-".join("-" * w for w in widths)]
    lines.extend(" | ".join(c.ljust(widths[i]) for i, c in enumerate(row)) for row in grid)
    return "\n".join(lines)


def render_info(payload):
    lines = [
        f"rows: {payload['rows']}   columns: {payload['columns']}   "
        f"encoding: {payload['encoding']}   delimiter: {payload['delimiter']!r}"
    ]
    if payload["profile"]:
        table = []
        for name, info in payload["profile"].items():
            if info["type"] in ("int", "float"):
                span = (f"{info['min']:.6g} .. {info['max']:.6g}"
                        if info["min"] is not None else "-")
                table.append([name, info["type"], str(info["missing"]), span])
            elif info["type"] == "text":
                table.append([name, info["type"], str(info["missing"]),
                              str(info.get("distinct", "-"))])
            else:
                table.append([name, info["type"], str(info["missing"]), "-"])
        lines.append(render_table(["column", "type", "missing", "distinct / range"], table))
    return "\n".join(lines)


def render_head(payload):
    if not payload["columns"]:
        return "(empty file)"
    out = render_table(payload["columns"], payload["rows"])
    remaining = payload["total"] - payload["shown"]
    if remaining > 0:
        out += f"\n... {remaining} more rows"
    return out


def render_stats(payload):
    if not payload["columns"]:
        return "(no columns)"
    header = ["column", "type", "n", "mean", "stdev", "min", "median", "max", "top values"]
    table = []
    for name, info in payload["columns"].items():
        if info["type"] in ("int", "float") and "mean" in info:
            fmt = lambda x: "-" if x is None else f"{x:.6g}"  # noqa: E731
            table.append([name, info["type"], str(info["n"]), fmt(info["mean"]),
                          fmt(info["stdev"]), fmt(info["min"]), fmt(info["median"]),
                          fmt(info["max"]), "-"])
        else:
            top = ", ".join(f"{v} ({c})" for v, c in info.get("top", []))
            table.append([name, info["type"], str(info["n"]),
                          "-", "-", "-", "-", "-", top or "-"])
    return render_table(header, table)


RENDER = {"info": render_info, "head": render_head, "stats": render_stats}


# ---- CLI ---------------------------------------------------------------
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="csvpeek", description="Peek into CSV files from the terminal."
    )
    parser.add_argument("--version", action="version", version=f"csvpeek {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("info", "head", "stats"):
        p = sub.add_parser(name, help=f"{name} view of a CSV file")
        p.add_argument("file", help="path to the CSV file")
        p.add_argument("--json", action="store_true", help="machine-readable output")
        p.add_argument("--encoding", help="force encoding (default: auto-detect)")
        p.add_argument("--delimiter", help="force delimiter (default: auto-detect)")
        if name == "head":
            p.add_argument("-n", type=int, default=5, help="rows to show (default: 5)")
        if name == "stats":
            p.add_argument("--cols", help="comma-separated subset of columns")

    args = parser.parse_args(argv)
    try:
        rows, enc, delim = load_rows(args.file, encoding=args.encoding,
                                     delimiter=args.delimiter)
    except FileNotFoundError:
        print(f"csvpeek: file not found: {args.file}", file=sys.stderr)
        return 1
    except (ValueError, UnicodeDecodeError) as exc:
        print(f"csvpeek: {exc}", file=sys.stderr)
        return 1

    try:
        if args.command == "info":
            payload = build_info_payload(rows, enc, delim)
        elif args.command == "head":
            payload = build_head_payload(rows, args.n)
        else:
            payload = build_stats_payload(rows, args.cols)
    except KeyError as exc:
        print(f"csvpeek: {exc.args[0]}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(RENDER[args.command](payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
