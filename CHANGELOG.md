# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]
### Planned
- `hist` subcommand: ASCII histogram for numeric columns

## [0.1.0] - 2026-10-03
### Added
- `info` / `head` / `stats` subcommands
- Column type inference (int / float / text / empty) and missing-value counts
- Numeric describe (mean, stdev, min, median, max) and categorical top values
- Encoding auto-detection (utf-8-sig / utf-8 / gbk / latin-1)
- Delimiter sniffing (`,` `;` TAB `|`)
- `--json` machine-readable output; exit code 1 on file errors
- Unit tests and CI on Python 3.9-3.13
