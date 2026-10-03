# csvpeek

[![CI](https://github.com/bilibiliUID1480494301/csvpeek/actions/workflows/ci.yml/badge.svg)](https://github.com/bilibiliUID1480494301/csvpeek/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

> Peek into CSV files from the terminal — info, head, stats, hist. No pandas required.
> 终端里的 CSV 速览工具：结构、前几行、快速统计、直方图，零依赖。

You just need to know *what's inside* `data.csv` — opening Excel is overkill and
`pandas` is 200 MB away. `csvpeek` is a single stdlib-only command.

## Install

```bash
pip install .            # from a clone
# or run in place:
python csvpeek.py --help
```

## Usage

```bash
csvpeek info sales.csv      # structure: rows, columns, types, missing values
csvpeek head sales.csv -n 5 # first rows, pretty table
csvpeek stats sales.csv     # numeric describe + categorical top values
csvpeek stats sales.csv --cols price,qty
csvpeek hist sales.csv --col amount --bins 8   # ASCII histogram of a numeric column
csvpeek info sales.csv --json   # machine-readable output for scripts
```

### Sample output

```text
$ csvpeek info sales.csv
rows: 128   columns: 5   encoding: gbk   delimiter: ','
column   | type | missing | distinct / range
---------+------+---------+------------------
order_id | int  | 0       | 1001 .. 1128
city     | text | 0       | 6
amount   | float| 3       | 12.5 .. 980.0
```

Encoding and delimiter are auto-detected (`utf-8-sig` / `utf-8` / `gbk` /
`latin-1`, and `,` `;` TAB `|`) — files exported from Excel on Chinese Windows
just work. Force them with `--encoding` / `--delimiter` when needed.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | success |
| `1` | file error (missing file, undecodable, unknown column) |

## Testing

```bash
python -m unittest discover -s tests -t . -v
```

## Roadmap

See the [open issues](../../issues) — `--sample`, TSV mode, optional xlsx support.

## License

[MIT](LICENSE)

---

> **AI-assisted development statement / AI 辅助开发声明**: this project was written
> with the help of an AI coding agent and is published as a real, working tool —
> every feature is covered by the unit tests in [`tests/`](tests/).
