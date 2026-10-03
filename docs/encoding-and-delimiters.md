# Encoding & delimiter detection

## Encoding candidates (tried in order)

1. `utf-8-sig` - UTF-8 with or without BOM (Excel's "CSV UTF-8")
2. `utf-8`
3. `gbk` - the default ANSI codepage on Simplified-Chinese Windows
4. `latin-1` - never fails; last resort

Override with `--encoding <name>` (any Python codec name, e.g. `utf-16`, `big5`).

## Delimiter candidates

`,` `;` TAB `|` - sniffed from the first 4 KB with `csv.Sniffer`; falls back to
`,` when the sample is ambiguous. Override with `--delimiter`.

## Notes

- Detection reads the whole file into memory; for very large files split or
  convert them first.
- `latin-1` never raises, so a wrong encoding "succeeds" with mojibake. If you
  see garbled text, force the real encoding, e.g. `--encoding gbk`.
- `utf-8-sig` first means BOM-prefixed files never leak a `\ufeff` into the
  first column name.
