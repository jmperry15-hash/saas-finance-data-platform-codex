"""Offline tests of the upload helper. These do NOT establish cloud success."""

import contextlib
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from scripts import cloud_shell_upload as uploader
from scripts import prepare_bigquery_bundle as builder
from src.synthetic.generate import ROOT, generate, load_config, write_tables


class UploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.base = Path(cls.temp.name)
        cfg = load_config(ROOT / "config/scenario.json")
        write_tables(generate(cfg), cls.base / "data/generated", cfg)
        for name in ("scripts/cloud_shell_upload.py", "docs/bigquery_bulk_upload.md"):
            target = cls.base / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        with patch.object(builder, "ROOT", cls.base), contextlib.redirect_stdout(io.StringIO()):
            archive = builder.build_bundle()
        with zipfile.ZipFile(archive) as z:
            cls.names = z.namelist()
            z.extractall(cls.base / "unpacked")
        cls.bundle = cls.base / "unpacked/saas-finance-upload"

    def test_package_has_only_allowlisted_files_and_explicit_types(self):
        manifest = uploader.validate_bundle(self.bundle)
        self.assertEqual(len(manifest["tables"]), 14)
        self.assertEqual(len(self.names), 31)
        self.assertEqual(sum(i["rows"] for i in manifest["tables"]), 23794)
        self.assertFalse(any("credential" in name or ".git/" in name for name in self.names))
        schema = json.loads((self.bundle / "schemas/workday/employees.json").read_text())
        fields = {f["name"]: f for f in schema}
        self.assertEqual(fields["employee_id"]["type"], "STRING")
        self.assertEqual(fields["annual_base_cents"]["type"], "INTEGER")
        self.assertEqual(fields["termination_date"]["type"], "DATE")
        self.assertEqual(fields["termination_date"]["mode"], "NULLABLE")

    def test_changed_csv_is_rejected_before_cloud_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "bundle"
            shutil.copytree(self.bundle, target)
            (target / "data/shared/departments.csv").write_text("corrupted")
            with patch.object(uploader, "command") as command:
                with self.assertRaisesRegex(ValueError, "Bundle file changed"):
                    uploader.upload("test-project-123", target)
                command.assert_not_called()

    def test_enabled_linked_or_unknown_billing_blocks_every_write(self):
        for response in ({"billingEnabled": True}, {}, {"billingEnabled": False, "billingAccountName": "billingAccounts/test"}):
            with self.subTest(response=response), patch.object(uploader.shutil, "which", return_value="tool"), patch.object(uploader, "command", return_value=response) as command:
                with self.assertRaisesRegex(ValueError, "billing"):
                    uploader.upload("test-project-123", self.bundle)
                self.assertEqual(command.call_count, 1)

    def fake_cloud(self, mismatch=False, wrong_region=False):
        manifest = uploader.validate_bundle(self.bundle)
        by_target = {"test-project-123:" + i["dataset"] + "." + i["table"]: i for i in manifest["tables"]}
        calls = []

        def fake(args, as_json=False):
            calls.append(args)
            if args[0] == "gcloud":
                return {"billingEnabled": False, "billingAccountName": ""}
            if "ls" in args:
                if args[-1] == "test-project-123:":
                    return [{"datasetReference": {"datasetId": "raw_shared"}}]
                return [{"tableReference": {"tableId": "departments"}}]
            if "show" in args:
                if args[-1] == "test-project-123:raw_shared":
                    return {"location": "EU" if wrong_region else "US"}
                item = by_target[args[-1]]
                return {"type": "TABLE", "numRows": str(item["rows"] + int(mismatch)),
                        "schema": {"fields": json.loads((self.bundle / item["schema"]).read_text())}}
            return ""
        return calls, fake

    def test_one_run_skips_correct_departments_and_loads_other_13(self):
        calls, fake = self.fake_cloud()
        with patch.object(uploader.shutil, "which", return_value="tool"), patch.object(uploader, "command", side_effect=fake), contextlib.redirect_stdout(io.StringIO()):
            uploader.upload("test-project-123", self.bundle)
        loads = [c for c in calls if "load" in c]
        self.assertEqual(len(loads), 13)
        self.assertTrue(all("--skip_leading_rows=1" in c and "--max_bad_records=0" in c for c in loads))
        self.assertFalse(any("--replace" in arg or "enable" == arg or "delete" == arg for c in calls for arg in c))
        self.assertEqual(sum("mk" in c for c in calls), 4)

    def test_existing_bad_header_import_stops_before_any_writes(self):
        calls, fake = self.fake_cloud(mismatch=True)
        with patch.object(uploader.shutil, "which", return_value="tool"), patch.object(uploader, "command", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "different schema or row count"):
                uploader.upload("test-project-123", self.bundle)
        self.assertFalse(any("mk" in c or "load" in c for c in calls))

    def test_wrong_region_stops_before_any_writes(self):
        calls, fake = self.fake_cloud(wrong_region=True)
        with patch.object(uploader.shutil, "which", return_value="tool"), patch.object(uploader, "command", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "not in US"):
                uploader.upload("test-project-123", self.bundle)
        self.assertFalse(any("mk" in c or "load" in c for c in calls))
