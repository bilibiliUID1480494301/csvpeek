"""Tests for csvpeek (stdlib only)."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import csvpeek


class BaseTestCase(unittest.TestCase):
    def write_csv(self, text, encoding="utf-8", suffix=".csv"):
        handle = tempfile.NamedTemporaryFile(
            "wb", suffix=suffix, delete=False, dir=tempfile.gettempdir()
        )
        handle.write(text.encode(encoding))
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def run_cli(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = csvpeek.main(list(argv))
        return code, buf.getvalue()


SAMPLE = (
    "name,age,city\n"
    "Alice,30,Beijing\n"
    "Bob,25,Shanghai\n"
    "Cindy,35,Beijing\n"
)


class LoadTests(BaseTestCase):
    def test_basic_load(self):
        path = self.write_csv(SAMPLE)
        rows, enc, delim = csvpeek.load_rows(path)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["name"], "Alice")
        self.assertEqual(enc, "utf-8-sig")
        self.assertEqual(delim, ",")

    def test_gbk_decoded(self):
        path = self.write_csv("name,city\n张三,北京\n李四,上海\n", encoding="gbk")
        rows, enc, _ = csvpeek.load_rows(path)
        self.assertEqual(enc, "gbk")
        self.assertEqual(rows[0]["city"], "北京")

    def test_semicolon_sniffed(self):
        path = self.write_csv("a;b\n1;2\n3;4\n")
        rows, _, delim = csvpeek.load_rows(path)
        self.assertEqual(delim, ";")
        self.assertEqual(rows[1]["b"], "4")

    def test_forced_encoding(self):
        path = self.write_csv("a\n1\n", encoding="utf-16")
        rows, enc, _ = csvpeek.load_rows(path, encoding="utf-16")
        self.assertEqual(enc, "utf-16")
        self.assertEqual(rows[0]["a"], "1")


class ProfileTests(BaseTestCase):
    def test_profile_column_kinds(self):
        self.assertEqual(csvpeek.profile_column(["1", "2", "3"]), "int")
        self.assertEqual(csvpeek.profile_column(["1.5", "2"]), "float")
        self.assertEqual(csvpeek.profile_column(["a", "b"]), "text")
        self.assertEqual(csvpeek.profile_column(["", None]), "empty")

    def test_profile_rows_summary(self):
        path = self.write_csv(SAMPLE)
        rows, _, _ = csvpeek.load_rows(path)
        profile = csvpeek.profile_rows(rows)
        self.assertEqual(profile["age"]["type"], "int")
        self.assertEqual(profile["age"]["missing"], 0)
        self.assertEqual(profile["city"]["distinct"], 2)
        self.assertEqual(profile["city"]["top"][0], ("Beijing", 2))

    def test_missing_values_counted(self):
        path = self.write_csv("a,b\n1,\n2,5\n,7\n")
        rows, _, _ = csvpeek.load_rows(path)
        profile = csvpeek.profile_rows(rows)
        self.assertEqual(profile["a"]["missing"], 1)
        self.assertEqual(profile["b"]["missing"], 1)


class CliTests(BaseTestCase):
    def setUp(self):
        self.path = self.write_csv(SAMPLE)

    def test_info_json(self):
        code, out = self.run_cli("info", self.path, "--json")
        self.assertEqual(code, 0)
        payload = json.loads(out)
        self.assertEqual(payload["rows"], 3)
        self.assertEqual(payload["profile"]["age"]["type"], "int")
        self.assertEqual(payload["profile"]["city"]["distinct"], 2)

    def test_info_human(self):
        code, out = self.run_cli("info", self.path)
        self.assertEqual(code, 0)
        self.assertIn("rows: 3", out)
        self.assertIn("int", out)

    def test_head_limits_rows(self):
        code, out = self.run_cli("head", self.path, "-n", "2")
        self.assertEqual(code, 0)
        self.assertIn("Alice", out)
        self.assertNotIn("Cindy", out)
        self.assertIn("1 more rows", out)

    def test_stats_numeric(self):
        code, out = self.run_cli("stats", self.path, "--cols", "age", "--json")
        self.assertEqual(code, 0)
        age = json.loads(out)["columns"]["age"]
        self.assertEqual(age["mean"], 30.0)
        self.assertEqual(age["min"], 25.0)
        self.assertEqual(age["max"], 35.0)
        self.assertEqual(age["median"], 30.0)
        self.assertEqual(age["n"], 3)

    def test_stats_categorical_top(self):
        code, out = self.run_cli("stats", self.path, "--cols", "city", "--json")
        self.assertEqual(code, 0)
        city = json.loads(out)["columns"]["city"]
        self.assertEqual(city["top"][0], ["Beijing", 2])

    def test_unknown_column_exit_1(self):
        code, _ = self.run_cli("stats", self.path, "--cols", "nope")
        self.assertEqual(code, 1)

    def test_missing_file_exit_1(self):
        code, _ = self.run_cli("info", "definitely-missing.csv")
        self.assertEqual(code, 1)

    def test_long_cell_truncated(self):
        path = self.write_csv("v\n" + "x" * 50 + "\n")
        code, out = self.run_cli("head", path)
        self.assertEqual(code, 0)
        self.assertIn("…", out)


if __name__ == "__main__":
    unittest.main()
