#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tarfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_ROOT.parent.parent


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_ROOT / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect_release_changes = load_script(
    "detect_release_changes", "detect-release-changes.py"
)
mark_generated_doc_review = load_script(
    "mark_generated_doc_review", "mark-generated-doc-review.py"
)
update_tidas_tools_pin = load_script(
    "update_tidas_tools_pin", "update-tidas-tools-pin.py"
)
update_tidas_spec_pin = load_script(
    "update_tidas_spec_pin", "update-tidas-spec-pin.py"
)
update_tidas_public_rules_pin = load_script(
    "update_tidas_public_rules_pin", "update-tidas-public-rules-pin.py"
)


class PublicRulesReleasePinTests(unittest.TestCase):
    def test_exact_archive_updates_rule_identity_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pin_path = root / update_tidas_public_rules_pin.SPEC_PIN
            rules_path = root / update_tidas_public_rules_pin.RULES_PIN
            assets = root / update_tidas_public_rules_pin.ASSET_ROOT
            pin_path.parent.mkdir(parents=True)
            assets.mkdir(parents=True)
            old_index = b'{"schema_version":1,"rules_version":"old"}\n'
            old_schema = b'{"type":"object"}\n'
            (assets / "public-rules.v1.json").write_bytes(old_index)
            (assets / "public-rules.v1.schema.json").write_bytes(old_schema)
            (assets / "public-rules.source.v1.json").write_text('{}\n')
            rules_path.write_text(json.dumps({
                "schema_version": "tidas.public-rules-source.v1",
                "repository": "https://github.com/tiangong-lca/tidas-spec.git",
                "commit": "a" * 40,
                "rules_version": "old",
                "assets": {
                    "index": {"path": update_tidas_public_rules_pin.RULES["index"], "sha256": hashlib.sha256(old_index).hexdigest()},
                    "schema": {"path": update_tidas_public_rules_pin.RULES["schema"], "sha256": hashlib.sha256(old_schema).hexdigest()},
                },
                "status": "released",
            }))

            index = b'{"schema_version":1,"rules_version":"2026.09.20"}\n'
            schema = b'{"type":"object","required":["rules"]}\n'
            files = {
                update_tidas_public_rules_pin.RULES["index"]: index,
                update_tidas_public_rules_pin.RULES["schema"]: schema,
            }
            manifest = json.dumps({
                "package": {"name": "@tiangong-lca/tidas-spec", "version": "0.2.3"},
                "files": [
                    {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
                    for path, data in files.items()
                ],
            }).encode()
            archive = root / "tiangong-lca-tidas-spec-0.2.3.tgz"
            with tarfile.open(archive, "w:gz") as tar:
                for path, data in {"spec-manifest.json": manifest, **files}.items():
                    info = tarfile.TarInfo(f"package/{path}")
                    info.size = len(data)
                    tar.addfile(info, io.BytesIO(data))
            pin_path.write_text(json.dumps({
                "package": "@tiangong-lca/tidas-spec",
                "version": "0.2.3",
                "sourceRef": "v0.2.3",
                "sourceCommit": "b" * 40,
                "archiveFile": archive.name,
                "archiveSha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "manifestSha256": hashlib.sha256(manifest).hexdigest(),
            }))

            self.assertTrue(update_tidas_public_rules_pin.update_public_rules(root, archive))
            self.assertFalse(update_tidas_public_rules_pin.update_public_rules(root, archive))
            updated = json.loads(rules_path.read_text())
            self.assertEqual(updated["commit"], "b" * 40)
            self.assertEqual(updated["rules_version"], "2026.09.20")
            self.assertEqual((assets / "public-rules.v1.json").read_bytes(), index)
            self.assertEqual((assets / "public-rules.v1.schema.json").read_bytes(), schema)
            identity = json.loads((assets / "public-rules.source.v1.json").read_text())
            self.assertEqual(identity["commit"], "b" * 40)
            self.assertEqual(identity["index_sha256"], hashlib.sha256(index).hexdigest())
            (assets / "public-rules.v1.json").write_bytes(b"tampered")
            with self.assertRaisesRegex(update_tidas_public_rules_pin.PublicRulesPinError, "has drifted"):
                update_tidas_public_rules_pin.update_public_rules(root, archive)
            (assets / "public-rules.v1.json").write_bytes(index)
            archive.write_bytes(archive.read_bytes() + b"tampered")
            with self.assertRaisesRegex(update_tidas_public_rules_pin.PublicRulesPinError, "digest conflicts"):
                update_tidas_public_rules_pin.update_public_rules(root, archive)



class ReleaseDetectionTests(unittest.TestCase):
    def test_untagged_current_version_is_release_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            (repo / "sdks/typescript").mkdir(parents=True)
            (repo / "sdks/python").mkdir(parents=True)
            (repo / "sdks/typescript/package.json").write_text(
                json.dumps({"version": "0.1.46"}), encoding="utf-8"
            )
            (repo / "sdks/python/pyproject.toml").write_text(
                'version = "0.2.14"\n', encoding="utf-8"
            )
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Automation Test"],
                check=True,
            )
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True
            )
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            subprocess.run(
                ["git", "-C", str(repo), "tag", "python-v0.2.14"], check=True
            )

            outputs = detect_release_changes.build_outputs(repo, head, head)
            self.assertEqual("true", outputs["typescript_changed"])
            self.assertEqual("typescript-v0.1.46", outputs["typescript_tag"])
            self.assertEqual("false", outputs["python_changed"])

            subprocess.run(
                ["git", "-C", str(repo), "tag", "typescript-v0.1.46"], check=True
            )
            outputs = detect_release_changes.build_outputs(repo, head, head)
            self.assertEqual("false", outputs["typescript_changed"])
            self.assertEqual("false", outputs["any_changed"])


class GeneratedDocReviewTests(unittest.TestCase):
    def test_review_metadata_is_deterministic_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            for relative_path in mark_generated_doc_review.MARKDOWN_DOCUMENTS:
                path = repo / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "---\n"
                    "lastReviewedAt: 2026-01-01\n"
                    "lastReviewedCommit: old\n"
                    "---\n",
                    encoding="utf-8",
                )
            config_path = repo / mark_generated_doc_review.CONFIG_DOCUMENT
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(
                'lastReviewedAt: "2026-01-01"\nlastReviewedCommit: "old"\n',
                encoding="utf-8",
            )

            kwargs = {
                "reviewed_at": "2026-07-27",
                "reviewed_commit": "a" * 40,
                "upstream_sha": "b" * 40,
            }
            mark_generated_doc_review.mark_documents(repo, **kwargs)
            first = {
                path: (repo / path).read_text(encoding="utf-8")
                for path in (
                    *mark_generated_doc_review.MARKDOWN_DOCUMENTS,
                    mark_generated_doc_review.CONFIG_DOCUMENT,
                )
            }
            mark_generated_doc_review.mark_documents(repo, **kwargs)
            second = {
                path: (repo / path).read_text(encoding="utf-8")
                for path in first
            }

            self.assertEqual(first, second)
            for relative_path, raw in second.items():
                self.assertIn("2026-07-27", raw, relative_path.as_posix())
                self.assertIn("a" * 40, raw, relative_path.as_posix())
            for relative_path in mark_generated_doc_review.MARKDOWN_DOCUMENTS:
                self.assertIn("b" * 40, second[relative_path])


class UpstreamPinTests(unittest.TestCase):
    def test_pin_update_is_exact_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repo = Path(temp_dir)
            pin_path = repo / update_tidas_tools_pin.SOURCE_HELPER
            pin_path.parent.mkdir(parents=True)
            pin_path.write_text(
                'TIDAS_TOOLS_SHA="${TIDAS_TOOLS_SHA:-' + "a" * 40 + '}"\n',
                encoding="utf-8",
            )

            update_tidas_tools_pin.update_pin(repo, "B" * 40)
            first = pin_path.read_text(encoding="utf-8")
            update_tidas_tools_pin.update_pin(repo, "B" * 40)
            second = pin_path.read_text(encoding="utf-8")

            self.assertEqual(first, second)
            self.assertIn("b" * 40, second)


class TidasSpecReleaseEventTests(unittest.TestCase):
    def test_receiver_reads_compact_release_options_and_legacy_fields(self) -> None:
        sync = (REPO_ROOT / ".github/workflows/sync-from-tidas-tools.yml").read_text(encoding="utf-8")
        self.assertIn('release_options = payload.get("release_options", {})', sync)
        self.assertIn('release_options.get("packages", payload.get("packages",', sync)
        self.assertIn('release_options.get("typescript_bump", payload.get("typescript_bump",', sync)
        self.assertIn('release_options.get("python_bump", payload.get("python_bump",', sync)

    def test_reviewed_candidate_promotes_only_to_exact_formal_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pin = Path(temp_dir) / "tidas-spec-pin.json"
            candidate = {
                "pinVersion": 1,
                "package": "@tiangong-lca/tidas-spec",
                "version": "0.2.0",
                "sourceCommit": "58dc72f5cb2d203a00388fec71d31091911f7dde",
                "sourceRef": "candidate/58dc72f5cb2d203a00388fec71d31091911f7dde",
                "archiveSha256": "45da9de790ffcdadd1984ffc3544c67a1503c0947470a629e8252aed19100228",
                "manifestSha256": "4677b9cf864326be9d430bf9760c754c4c0c1905d90e62c161655a159fd758c7",
                "releaseArchiveUrl": "https://raw.githubusercontent.com/tiangong-lca/tidas-spec/58dc72f5cb2d203a00388fec71d31091911f7dde/release/tiangong-lca-tidas-spec-0.2.0.tgz",
                "repositoryAuthoredPaths": ["assets/tidas/schema.lock.json"],
                "note": "This candidate pin is not a formal tidas-spec release.",
            }
            pin.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
            candidate_bytes = pin.read_bytes()
            payload = self.base_payload()
            payload.update({
                "source_commit": "f71ed3002048f0f6a858b93e6e71830ef16a7145",
                "archive_sha256": "40adef78b3691a7327c282afd2e0eb1a93aa38804610e9ef87c43fea9ccffda2",
                "manifest_sha256": "a6ce771bd06a601c6defdddb1e49a694e42f4a9a0d549f28ca88a45ef830f75d",
            })
            payload["event_key"] = f"{payload['package']}@{payload['version']}:{payload['archive_sha256']}:{payload['manifest_sha256']}"
            conflicting = dict(payload, source_commit="d" * 40)
            with self.assertRaises(update_tidas_spec_pin.SpecPinError):
                update_tidas_spec_pin.apply_event(pin, conflicting)
            self.assertEqual(pin.read_bytes(), candidate_bytes)
            self.assertTrue(update_tidas_spec_pin.apply_event(pin, payload))
            self.assertFalse(update_tidas_spec_pin.apply_event(pin, payload))
            promoted = json.loads(pin.read_text(encoding="utf-8"))
            self.assertEqual(promoted["sourceRef"], "v0.2.0")
            self.assertNotIn("repositoryAuthoredPaths", promoted)
            self.assertNotIn("note", promoted)
            with self.assertRaises(update_tidas_spec_pin.SpecPinError):
                update_tidas_spec_pin.apply_event(pin, conflicting)

    def test_identical_candidate_promotes_to_formal_release(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pin = Path(temp_dir) / "tidas-spec-pin.json"
            version = "0.2.2"
            candidate_commit = "8" * 40
            archive_sha = "a" * 64
            manifest_sha = "b" * 64
            archive_file = f"tiangong-lca-tidas-spec-{version}.tgz"
            candidate = {
                "pinVersion": 1,
                "package": "@tiangong-lca/tidas-spec",
                "version": version,
                "sourceCommit": candidate_commit,
                "sourceRef": f"candidate/{candidate_commit}",
                "archiveFile": archive_file,
                "archiveSha256": archive_sha,
                "manifestSha256": manifest_sha,
                "releaseArchiveUrl": (
                    "https://raw.githubusercontent.com/tiangong-lca/tidas-spec/"
                    f"{candidate_commit}/release/{archive_file}"
                ),
                "repositoryAuthoredPaths": ["assets/tidas/schema.lock.json"],
                "note": "Immutable reviewed candidate input; this candidate pin is not a formal tidas-spec release.",
            }
            pin.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
            payload = self.base_payload(version=version)
            payload.update({
                "source_commit": "c" * 40,
                "archive_sha256": archive_sha,
                "manifest_sha256": manifest_sha,
            })
            payload["event_key"] = (
                f"{payload['package']}@{version}:{archive_sha}:{manifest_sha}"
            )

            self.assertTrue(update_tidas_spec_pin.apply_event(pin, payload))
            self.assertFalse(update_tidas_spec_pin.apply_event(pin, payload))
            promoted = json.loads(pin.read_text(encoding="utf-8"))
            self.assertEqual(promoted["sourceCommit"], "c" * 40)
            self.assertEqual(promoted["sourceRef"], "v0.2.2")
            self.assertNotIn("repositoryAuthoredPaths", promoted)
            self.assertNotIn("note", promoted)

    def test_identical_candidate_promotion_requires_candidate_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pin = Path(temp_dir) / "tidas-spec-pin.json"
            self.write_pin(pin, version="0.2.2")
            payload = self.base_payload(version="0.2.2")
            current = json.loads(pin.read_text(encoding="utf-8"))
            payload["archive_sha256"] = current["archiveSha256"]
            payload["manifest_sha256"] = current["manifestSha256"]
            payload["event_key"] = (
                f"{payload['package']}@0.2.2:{payload['archive_sha256']}:"
                f"{payload['manifest_sha256']}"
            )
            with self.assertRaises(update_tidas_spec_pin.SpecPinError):
                update_tidas_spec_pin.apply_event(pin, payload)

    def base_payload(self, version: str = "0.2.0") -> dict:
        archive_sha = "a" * 64
        manifest_sha = "b" * 64
        return {
            "event_key": f"@tiangong-lca/tidas-spec@{version}:{archive_sha}:{manifest_sha}",
            "package": "@tiangong-lca/tidas-spec",
            "version": version,
            "source_commit": "c" * 40,
            "archive_file": f"tiangong-lca-tidas-spec-{version}.tgz",
            "archive_url": f"https://github.com/tiangong-lca/tidas-spec/releases/download/v{version}/tiangong-lca-tidas-spec-{version}.tgz",
            "archive_sha256": archive_sha,
            "manifest_sha256": manifest_sha,
            "packages": ["typescript", "python"],
        }

    def write_pin(self, path: Path, version: str = "0.1.0") -> None:
        path.write_text(json.dumps({
            "pinVersion": 1,
            "package": "@tiangong-lca/tidas-spec",
            "version": version,
            "sourceCommit": "1" * 40,
            "sourceRef": f"v{version}",
            "archiveFile": f"tiangong-lca-tidas-spec-{version}.tgz",
            "archiveSha256": "2" * 64,
            "manifestFile": "spec-manifest.json",
            "manifestPathInArchive": "package/spec-manifest.json",
            "manifestSha256": "3" * 64,
            "releaseArchiveUrl": f"https://github.com/tiangong-lca/tidas-spec/releases/download/v{version}/tiangong-lca-tidas-spec-{version}.tgz",
            "repositoryAuthoredPaths": ["assets/tidas/schemas/candidate-only.json"],
            "note": "candidate-only provenance",
        }, indent=2) + "\n", encoding="utf-8")

    def test_new_event_updates_pin_and_exact_replay_is_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pin = Path(temp_dir) / "tidas-spec-pin.json"
            self.write_pin(pin)
            payload = self.base_payload()
            self.assertTrue(update_tidas_spec_pin.apply_event(pin, payload))
            first = pin.read_text(encoding="utf-8")
            self.assertFalse(update_tidas_spec_pin.apply_event(pin, payload))
            self.assertEqual(first, pin.read_text(encoding="utf-8"))
            updated = json.loads(first)
            self.assertEqual(updated["sourceCommit"], "c" * 40)
            self.assertEqual(updated["archiveSha256"], "a" * 64)
            self.assertNotIn("repositoryAuthoredPaths", updated)
            self.assertNotIn("note", updated)

    def test_stale_and_conflicting_events_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pin = Path(temp_dir) / "tidas-spec-pin.json"
            self.write_pin(pin, version="0.2.0")
            stale = self.base_payload()
            stale["version"] = "0.1.9"
            stale["archive_file"] = "tiangong-lca-tidas-spec-0.1.9.tgz"
            stale["archive_url"] = "https://github.com/tiangong-lca/tidas-spec/releases/download/v0.1.9/tiangong-lca-tidas-spec-0.1.9.tgz"
            stale["event_key"] = f"@tiangong-lca/tidas-spec@0.1.9:{stale['archive_sha256']}:{stale['manifest_sha256']}"
            with self.assertRaises(update_tidas_spec_pin.SpecPinError):
                update_tidas_spec_pin.apply_event(pin, stale)
            conflict = self.base_payload()
            conflict["source_commit"] = "d" * 40
            conflict["event_key"] = f"@tiangong-lca/tidas-spec@0.2.0:{conflict['archive_sha256']}:{conflict['manifest_sha256']}"
            with self.assertRaises(update_tidas_spec_pin.SpecPinError):
                update_tidas_spec_pin.apply_event(pin, conflict)

    def test_malformed_or_partial_event_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pin = Path(temp_dir) / "tidas-spec-pin.json"
            self.write_pin(pin)
            payload = self.base_payload()
            payload.pop("manifest_sha256")
            with self.assertRaises(update_tidas_spec_pin.SpecPinError):
                update_tidas_spec_pin.apply_event(pin, payload)


class PythonArtifactRoundtripTests(unittest.TestCase):
    def make_distributions(self, root: Path) -> None:
        with zipfile.ZipFile(root / "tidas_sdk-0.3.0-py3-none-any.whl", "w") as archive:
            archive.writestr("tidas_sdk-0.3.0.dist-info/METADATA", "Name: tidas-sdk\nVersion: 0.3.0\n")
        with tarfile.open(root / "tidas_sdk-0.3.0.tar.gz", "w:gz") as archive:
            content = b"Name: tidas-sdk\nVersion: 0.3.0\n"
            entry = tarfile.TarInfo("tidas_sdk-0.3.0/PKG-INFO")
            entry.size = len(content)
            archive.addfile(entry, io.BytesIO(content))

    def run_inventory(self, mode: str, root: Path, expected: str = ""):
        return subprocess.run(
            [sys.executable, str(SCRIPT_ROOT / "python-dist-inventory.py"), mode, str(root)],
            env={**os.environ, "PYTHON_DIST_INVENTORY": expected},
            text=True, capture_output=True,
        )

    def test_roundtrip_binds_producer_bytes_and_rejects_missing_extra_or_corrupt_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_distributions(root)
            created = self.run_inventory("create", root)
            self.assertEqual(created.returncode, 0, created.stderr)
            expected = created.stdout.strip()
            self.assertEqual(self.run_inventory("verify", root, expected).returncode, 0)
            # A readable, valid archive with different bytes must fail the independently
            # supplied producer inventory, even if its own local inventory is coherent.
            wheel = root / "tidas_sdk-0.3.0-py3-none-any.whl"
            with zipfile.ZipFile(wheel, "a") as archive:
                archive.writestr("tidas_sdk/changed.py", "changed = True\n")
            changed = self.run_inventory("verify", root, expected)
            self.assertNotEqual(changed.returncode, 0)
            self.assertIn("differs from producer", changed.stderr)
            wheel.write_bytes(b"not a wheel")
            self.assertNotEqual(self.run_inventory("create", root).returncode, 0)
            wheel.unlink()
            self.assertNotEqual(self.run_inventory("verify", root, expected).returncode, 0)
            self.make_distributions(root)
            (root / "inventory.json").write_text(expected)
            self.assertNotEqual(self.run_inventory("verify", root, expected).returncode, 0)

    def test_ci_roundtrip_has_independent_inventory_and_read_only_same_run_transfer(self):
        raw = (REPO_ROOT / ".github/workflows/ci.yml").read_text()
        producer, consumer = raw.split("  python-artifact-roundtrip:\n", 1)
        self.assertIn("dist-inventory: ${{ steps.inventory.outputs.inventory }}", producer)
        self.assertIn("./scripts/ci/verify-python-package.sh", producer)
        self.assertLess(producer.index("./scripts/ci/verify-python-package.sh"),
                        producer.index("Record producer distribution inventory"))
        self.assertIn("retention-days: 1", producer)
        self.assertIn("path: sdks/python/dist/*", producer)
        self.assertIn("archive: true", producer)
        self.assertIn("needs: python", consumer)
        self.assertIn("PYTHON_DIST_INVENTORY: ${{ needs.python.outputs.dist-inventory }}", consumer)
        self.assertIn("python3 scripts/ci/python-dist-inventory.py verify dist", consumer)
        self.assertIn("digest-mismatch: error", consumer)
        self.assertIn("skip-decompress: false", consumer)
        self.assertIn("actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9", producer)
        self.assertIn("actions/download-artifact@9000827ccba6bdab643e8b6fd33ac0654aef8333", consumer)
        for forbidden in ("secrets.", "id-token:", "environment:", "pull_request_target:",
                          "repository_dispatch:", "run-id:", "github-token:"):
            self.assertNotIn(forbidden, raw)

    def test_uv_cache_policy_is_explicit_at_the_four_existing_sites(self):
        for name in ("ci", "publish", "sync-from-tidas-tools", "tag-release-from-merge"):
            raw = (REPO_ROOT / ".github/workflows" / f"{name}.yml").read_text()
            with self.subTest(workflow=name):
                self.assertEqual(raw.count("enable-cache: auto"), 1)
                self.assertEqual(raw.count("prune-cache: false"), 1)
                self.assertNotIn("enable-cache: true", raw)


class PnpmWorkflowContractTests(unittest.TestCase):
    TYPESCRIPT_WORKFLOWS = (
        "ci.yml",
        "publish.yml",
        "sync-from-tidas-tools.yml",
        "tag-release-from-merge.yml",
    )

    def workflow_text(self, name: str) -> str:
        return (REPO_ROOT / ".github/workflows" / name).read_text(encoding="utf-8")

    def test_typescript_workflows_use_the_pnpm_11_setup_action(self) -> None:
        for name in self.TYPESCRIPT_WORKFLOWS:
            with self.subTest(workflow=name):
                raw = self.workflow_text(name)
                self.assertIn(
                    "uses: pnpm/setup@a0881977cd8ea73b1ed212236c99ca10dcc80cf4 "
                    "# v3.1.1",
                    raw,
                )
                self.assertIn("runtime: node@24.19.0", raw)
                self.assertIn("install: false", raw)
                self.assertIn("cache: true", raw)
                self.assertNotIn("pnpm/action-setup", raw)
                self.assertNotIn("actions/setup-node", raw)
                self.assertNotIn("cache: npm", raw)
                self.assertNotIn("package-lock.json", raw)
                self.assertNotIn("npm install --global", raw)

    def test_release_automation_uses_filtered_pnpm_commands(self) -> None:
        publish = self.workflow_text("publish.yml")
        typescript_publish_job = publish.split("  typescript-publish:\n", 1)[1].split(
            "\n  python-build:\n", 1
        )[0]
        self.assertIn("id-token: write", typescript_publish_job)
        self.assertNotIn("NPM_TOKEN", typescript_publish_job)
        self.assertNotIn("NODE_AUTH_TOKEN", typescript_publish_job)
        self.assertIn(
            "pnpm --filter @tiangong-lca/tidas-sdk --fail-if-no-match publish "
            "--access public --provenance --no-git-checks",
            publish,
        )

        sync = self.workflow_text("sync-from-tidas-tools.yml")
        self.assertIn(
            'pnpm --filter @tiangong-lca/tidas-sdk --fail-if-no-match version '
            '"$TYPESCRIPT_VERSION" --no-git-tag-version --no-git-checks',
            sync,
        )

    def test_sync_workflow_accepts_exact_spec_release_events(self) -> None:
        sync = self.workflow_text("sync-from-tidas-tools.yml")
        self.assertIn("- tidas_spec_released", sync)
        self.assertIn("update-tidas-spec-pin.py", sync)
        self.assertIn("update-tidas-public-rules-pin.py", sync)
        self.assertIn("TIDAS_SPEC_ARCHIVE_PATH", sync)
        self.assertIn("spec_archive_sha256", sync)
        self.assertIn("event_key", sync)
        self.assertIn("source_event", sync)
        self.assertIn("tidas_spec_released", sync)
        self.assertIn("update_tools_pin", sync)


class UpstreamIdentityMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        config = self.root / "empty.gitconfig"
        config.write_text("")
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(config))
        self.source = self.root / "source"
        self.git("init", "-q", str(self.source))
        self.git("-C", str(self.source), "config", "user.name", "Fixture")
        self.git("-C", str(self.source), "config", "user.email", "fixture@example.invalid")
        self.git("-C", str(self.source), "config", "commit.gpgsign", "false")
        (self.source / "marker").write_text("exact source")
        self.git("-C", str(self.source), "add", "marker")
        self.git("-C", str(self.source), "commit", "-qm", "fixture")
        self.sha = self.git("-C", str(self.source), "rev-parse", "HEAD")
        self.remote = self.root / "upstream.git"
        self.git("clone", "--bare", "-q", str(self.source), str(self.remote))
        self.canonical = "https://github.com/tiangong-lca/tidas-toolkit.git"
        self.env.update({
            "GIT_CONFIG_COUNT": "3",
            "GIT_CONFIG_KEY_0": f"url.{self.remote.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": self.canonical,
            "GIT_CONFIG_KEY_1": "credential.https://github.com.username",
            "GIT_CONFIG_VALUE_1": "selected-account",
            "GIT_CONFIG_KEY_2": "core.worktree",
            "GIT_CONFIG_VALUE_2": str(self.source),
        })
        self.marker = self.root / "asset-check.marker"
        self.resolver = self.root / "verify-assets.cjs"
        self.resolver.write_text("require('node:fs').writeFileSync(process.env.ASSET_TEST_MARKER, process.argv[3]); process.exit(process.env.ASSET_TEST_REJECT === '1' ? 1 : 0);")

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], env=self.env, text=True, stderr=subprocess.DEVNULL).strip()

    def resolve(self, **overrides: str):
        env = {**self.env, "TIDAS_TOOLS_SOURCE_MODE": "clone", "TIDAS_TOOLS_SHA": self.sha,
               "SDK_TEST_ASSET_RESOLVER": str(self.resolver), "ASSET_TEST_MARKER": str(self.marker),
               "GIT_DIR": str(self.source / ".git"), "GIT_INDEX_FILE": str(self.root / "foreign-index"), **overrides}
        script = "source " + shlex.quote(str(SCRIPT_ROOT / "lib/tidas-tools-source.sh")) + "\n" + r'''
trap cleanup_tidas_tools_source EXIT
TIDAS_TOOLS_ASSET_RESOLVER="$SDK_TEST_ASSET_RESOLVER"
resolve_tidas_tools_source "$SDK_TEST_ROOT"
printf 'ROOT=%s\n' "$RESOLVED_TIDAS_TOOLS_PATH"
printf 'TOP=%s\n' "$(upstream_git -C "$RESOLVED_TIDAS_TOOLS_PATH" rev-parse --show-toplevel)"
printf 'URL=%s\n' "$(upstream_git -C "$RESOLVED_TIDAS_TOOLS_PATH" config --get remote.origin.url)"
printf 'ACCOUNT=%s\n' "$(upstream_git -C "$RESOLVED_TIDAS_TOOLS_PATH" config --get credential.https://github.com.username)"
'''
        return subprocess.run(["bash", "-e", "-c", script], env={**env, "SDK_TEST_ROOT": str(REPO_ROOT)}, text=True, capture_output=True)

    def test_exact_clone_preserves_account_config_and_isolates_parent_git_bindings(self) -> None:
        result = self.resolve()
        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        self.assertEqual(values["URL"], self.canonical)
        self.assertEqual(values["ACCOUNT"], "selected-account")
        self.assertEqual(Path(values["ROOT"]).resolve(), Path(values["TOP"]).resolve())
        self.assertNotEqual(values["TOP"], str(self.source))
        self.assertTrue(self.marker.exists())
        self.assertFalse((self.root / "foreign-index").exists())

    def test_wrong_pin_and_rejected_assets_remain_blocking(self) -> None:
        result = self.resolve(TIDAS_TOOLS_SHA="0" * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.marker.exists())
        result = self.resolve(ASSET_TEST_REJECT="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.marker.exists())

    def test_real_workflow_clone_stores_no_automation_credential(self) -> None:
        text = (REPO_ROOT / ".github/workflows/sync-from-tidas-tools.yml").read_text()
        block = text.split("      - name: Clone upstream tidas-tools\n", 1)[1].split("      - name: Fetch and pin exact tidas-spec release", 1)[0]
        run = block.split("        run: |\n", 1)[1]
        commands = "\n".join(line[10:] for line in run.splitlines())
        # The workflow is a CI process, not a parent hook; core.worktree is tested
        # through the shared helper separately above.
        env = {**self.env, "GIT_CONFIG_COUNT": "2", "RUNNER_TEMP": str(self.root / "runner"), "REQUESTED_SHA": self.sha, "GITHUB_OUTPUT": str(self.root / "outputs"), "AUTOMATION_TOKEN": "sentinel-must-not-persist"}
        Path(env["RUNNER_TEMP"]).mkdir()
        result = subprocess.run(["bash", "-e", "-c", commands], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        clone = Path(env["RUNNER_TEMP"]) / "tidas-tools-upstream"
        raw = subprocess.check_output(["git", "-C", str(clone), "config", "--get", "remote.origin.url"], env=env, text=True).strip()
        self.assertEqual(raw, self.canonical)
        self.assertNotIn("sentinel", raw)
        self.assertIn("resolved_sha=" + self.sha, Path(env["GITHUB_OUTPUT"]).read_text())



class TypescriptVerifySourceConsistencyTests(unittest.TestCase):
    """The TypeScript verify chain must resolve the pinned upstream exactly once and
    keep generate/build/pack on that same verified checkout. A different or injected
    sibling checkout must never influence generated or built artifacts."""

    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        config = self.root / "empty.gitconfig"
        config.write_text("")
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(config))
        self.canonical = "https://github.com/tiangong-lca/tidas-toolkit.git"

        def write_tools_checkout(directory: Path, marker: str) -> str:
            directory.mkdir(parents=True)
            methodologies = directory / "assets" / "tidas" / "methodologies"
            methodologies.mkdir(parents=True)
            entries = []
            for name in ("tidas_flows.yaml", "tidas_processes.yaml"):
                body = f"# {marker}\nflows: []\n" if name == "tidas_flows.yaml" else f"# {marker}\nprocesses: []\n"
                target = methodologies / name
                target.write_text(body)
                entries.append(
                    {
                        "path": f"assets/tidas/methodologies/{name}",
                        "kind": "methodology",
                        "sha256": hashlib.sha256(body.encode()).hexdigest(),
                        "bytes": len(body.encode()),
                    }
                )
            lock = {
                "schema_version": "tidas.asset-lock.v1",
                "source_roots": ["assets/tidas"],
                "entries": entries,
            }
            (directory / "assets" / "asset-lock.v1.json").write_text(json.dumps(lock, indent=2))
            (directory / "marker").write_text(marker)
            self.git("init", "-q", str(directory))
            self.git("-C", str(directory), "config", "user.name", "Fixture")
            self.git("-C", str(directory), "config", "user.email", "fixture@example.invalid")
            self.git("-C", str(directory), "config", "commit.gpgsign", "false")
            self.git("-C", str(directory), "add", "-A")
            self.git("-C", str(directory), "commit", "-qm", f"checkout {marker}")
            return self.git("-C", str(directory), "rev-parse", "HEAD")

        self.source = self.root / "pinned-source"
        self.pin_sha = write_tools_checkout(self.source, "fixture-set-X")
        self.remote = self.root / "upstream.git"
        self.git("clone", "--bare", "-q", str(self.source), str(self.remote))
        self.sibling = self.root / "sibling" / "tidas-tools"
        self.sibling_sha = write_tools_checkout(self.sibling, "sibling-set-Y")
        self.assertNotEqual(self.pin_sha, self.sibling_sha)
        self.resolver = SCRIPT_ROOT / "tidas-tools-assets.mjs"
        # Stage TMPDIR lives inside the fixture-owned directory so test checkouts
        # are always cleaned up with the fixture.
        self.fixture_tmp = self.root / "tmp"
        self.fixture_tmp.mkdir()
        # The tag workflow runs these checks before package bootstrap. Fail loudly
        # if a regression accidentally introduces a pnpm requirement again.
        blocked_bin = self.root / "no-package-tooling"
        blocked_bin.mkdir()
        pnpm = blocked_bin / "pnpm"
        pnpm.write_text("#!/bin/sh\necho 'pnpm is unavailable before package bootstrap' >&2\nexit 127\n")
        pnpm.chmod(0o755)
        self.env["PATH"] = str(blocked_bin) + os.pathsep + self.env["PATH"]

    def git(self, *args: str) -> str:
        return subprocess.check_output(["git", *args], env=self.env, text=True, stderr=subprocess.DEVNULL).strip()

    def source_env(self) -> dict:
        env = {
            **self.env,
            "TIDAS_TOOLS_SOURCE_MODE": "clone",
            "TIDAS_TOOLS_SHA": self.pin_sha,
            "TIDAS_TOOLS_REPO_URL": self.canonical,
            "TIDAS_TOOLS_ASSET_RESOLVER": str(self.resolver),
            # Route the canonical URL to the local fixture remote, like the
            # UpstreamIdentityMigrationTests insteadOf mapping does.
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": f"url.{self.remote.as_uri()}.insteadOf",
            "GIT_CONFIG_VALUE_0": self.canonical,
            # Injected foreign path: clone mode must ignore it entirely.
            "TIDAS_TOOLS_PATH": str(self.sibling),
        }
        return env

    def test_verify_prelude_defaults_to_clone_and_exports_only_pinned_content(self) -> None:
        # Execute the real verify-typescript-package.sh prelude (SCRIPT_DIR through the
        # source/mode/trap/resolve wiring) with TIDAS_TOOLS_SOURCE_MODE unset: the script
        # must default to clone (a temp verified checkout), not the helper's auto default
        # that would select the unverified sibling and fail the pin check.
        script_text = (REPO_ROOT / "scripts/ci/verify-typescript-package.sh").read_text()
        boundary = script_text.index("before_generated_state=")
        prelude = "\n".join(script_text[:boundary].splitlines()[:-1])
        real_script_dir = 'SCRIPT_DIR=' + shlex.quote(str(SCRIPT_ROOT))
        prelude = re.sub(
            r'SCRIPT_DIR=.*',
            real_script_dir,
            prelude,
            count=1,
        )
        # This focused test exercises the tidas-tools source prelude only. The
        # complete spec-archive contract has its own dependency-free Node tests;
        # keep this fixture offline by replacing the new archive resolution block
        # with a no-op rather than reaching the network.
        prelude = prelude.replace('resolve_tidas_spec_source "$REPO_ROOT"', ': # spec archive is out of scope for this tools-source fixture')
        prelude = re.sub(
            r'export TIDAS_SPEC_SCHEMA_DIR=.*\nexport TIDAS_SPEC_METHODOLOGY_DIR=.*\nexport TIDAS_SPEC_ASSET_ROOT=.*',
            ': # spec archive is out of scope for this tools-source fixture',
            prelude,
        )
        lines = [
            "unset TIDAS_TOOLS_SOURCE_MODE",
            prelude,
            'printf "MODE=%s\\n" "$TIDAS_TOOLS_SOURCE_MODE"',
            'printf "PATH=%s\\n" "$TIDAS_TOOLS_PATH"',
            'printf "SHA=%s\\n" "$(upstream_git -C "$TIDAS_TOOLS_PATH" rev-parse HEAD)"',
            shlex.quote(sys.executable) + " -c " + shlex.quote(
                "import os; from pathlib import Path; "
                "print('CHILD_MARKER=' + (Path(os.environ['TIDAS_TOOLS_PATH']) / 'marker').read_text())"
            ),
            "",
        ]
        unset_env = self.source_env()
        unset_env["TMPDIR"] = str(self.fixture_tmp)
        result = subprocess.run(
            ["bash", "-e", "-c", "\n".join(lines)],
            env=unset_env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        self.assertEqual(values["MODE"], "clone")
        self.assertIn("/tidas-tools.", values["PATH"])
        self.assertNotEqual(values["PATH"], str(self.sibling))
        self.assertEqual(values["SHA"], self.pin_sha)
        self.assertEqual(values["CHILD_MARKER"], "fixture-set-X")
        self.assertFalse(Path(values["PATH"]).exists(), "verify must clean its owned clone")

    def test_generate_verified_path_reuse_revalidates_and_rejects_foreign_checkouts(self) -> None:
        # generate re-resolves in verified-path mode inside the same live checkout
        # lifetime: it must reuse the exact verified checkout (no second clone,
        # caller-owned lifetime) and stay fail-closed for foreign checkouts.
        script = (
            "source " + shlex.quote(str(SCRIPT_ROOT / "lib/tidas-tools-source.sh"))
            + "\nTIDAS_TOOLS_ASSET_RESOLVER=\"$SDK_RESOLVER\""
            + "\nTIDAS_TOOLS_SOURCE_MODE=clone"
            + "\nexport TIDAS_TOOLS_SOURCE_MODE"
            + "\ntrap cleanup_tidas_tools_source EXIT"
            + '\nresolve_tidas_tools_source "$SDK_TEST_ROOT"'
            + '\nexport TIDAS_TOOLS_PATH="$RESOLVED_TIDAS_TOOLS_PATH"'
            + '\nprintf "CLONE=%s\\n" "$TIDAS_TOOLS_PATH"'
            + "\nTIDAS_TOOLS_SOURCE_MODE=verified-path"
            + '\nresolve_tidas_tools_source "$SDK_TEST_ROOT"'
            + '\nprintf "REUSED=%s\\n" "$RESOLVED_TIDAS_TOOLS_PATH"'
            + '\nprintf "REUSED_TEMP=%s\\n" "$RESOLVED_TIDAS_TOOLS_IS_TEMP"'
        )
        env = {
            **self.source_env(),
            "SDK_TEST_ROOT": str(REPO_ROOT),
            "SDK_RESOLVER": str(self.resolver),
            "TMPDIR": str(self.fixture_tmp),
            # Injected foreign path before resolution: clone ignores it.
            "TIDAS_TOOLS_PATH": str(self.sibling),
        }
        ok = subprocess.run(
            ["bash", "-e", "-c", script],
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertEqual(
            ok.returncode,
            0,
            f"stdout={ok.stdout!r} stderr={ok.stderr!r} script={script!r} env_TTP={env['TIDAS_TOOLS_PATH']!r}",
        )
        values = dict(line.split("=", 1) for line in ok.stdout.splitlines() if "=" in line)
        self.assertNotEqual(values["CLONE"], str(self.sibling))
        self.assertEqual(values["REUSED"], values["CLONE"])
        self.assertEqual(values["REUSED_TEMP"], "0")
        # verified-path revalidation must reject a foreign checkout (commit mismatch):
        # point TIDAS_TOOLS_PATH at the sibling AFTER resolution, replay only the
        # verified-path stage, and observe the fail-closed rejection.
        foreign_script = script.replace(
            "TIDAS_TOOLS_SOURCE_MODE=clone",
            "TIDAS_TOOLS_SOURCE_MODE=clone\nTIDAS_TOOLS_PATH=" + shlex.quote(str(self.sibling)),
            1,
        ).replace(
            '\nexport TIDAS_TOOLS_PATH="$RESOLVED_TIDAS_TOOLS_PATH"',
            '\nexport TIDAS_TOOLS_PATH="$TIDAS_TOOLS_PATH"',
            1,
        )
        foreign = subprocess.run(
            ["bash", "-e", "-c", foreign_script],
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(foreign.returncode, 0)
        self.assertIn("commit mismatch", foreign.stderr)

    def test_auto_mode_prefers_the_canonical_sibling_and_keeps_the_legacy_one(self) -> None:
        # Auto mode must probe the canonical sibling directory before the
        # pre-rename one, keep an explicit TIDAS_TOOLS_PATH authoritative, and
        # still resolve a checkout that only has the legacy layout.
        sibling_root = self.root / "sibling"
        legacy = sibling_root / "tidas-tools"
        shutil.rmtree(legacy)
        canonical = sibling_root / "tidas-toolkit"
        explicit = self.root / "explicit" / "tidas-toolkit"
        for directory in (canonical, legacy, explicit):
            # Copy the pinned checkout so every candidate passes the exact-SHA
            # verification; only the directory name differs between them.
            shutil.copytree(self.source, directory)
        repo_root = sibling_root / "sdk-repo"
        # The sibling candidates are reached through "$repo_root/..", so the
        # repository root itself has to exist for the path to resolve.
        repo_root.mkdir()
        script = (
            "source " + shlex.quote(str(SCRIPT_ROOT / "lib/tidas-tools-source.sh"))
            + '\nTIDAS_TOOLS_ASSET_RESOLVER="$SDK_RESOLVER"'
            + "\nTIDAS_TOOLS_SOURCE_MODE=auto"
            + "\nexport TIDAS_TOOLS_SOURCE_MODE"
            + "\ntrap cleanup_tidas_tools_source EXIT"
            + '\nresolve_tidas_tools_source "$SDK_REPO_ROOT"'
            + '\nprintf "RESOLVED=%s\\n" "$RESOLVED_TIDAS_TOOLS_PATH"'
            + '\nprintf "TEMP=%s\\n" "$RESOLVED_TIDAS_TOOLS_IS_TEMP"'
        )
        env = {
            **self.env,
            "SDK_REPO_ROOT": str(repo_root),
            "SDK_RESOLVER": str(self.resolver),
            "TIDAS_TOOLS_SHA": self.pin_sha,
            "TIDAS_TOOLS_REPO_URL": self.canonical,
            "TIDAS_TOOLS_ASSET_RESOLVER": str(self.resolver),
            "TIDAS_TOOLS_PATH": "",
        }

        def resolve_with(extra_env: dict) -> dict:
            result = subprocess.run(
                ["bash", "-e", "-c", script],
                env={**env, **extra_env},
                text=True,
                capture_output=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"stdout={result.stdout!r} stderr={result.stderr!r} extra_env={extra_env!r}",
            )
            return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)

        values = resolve_with({})
        self.assertTrue(
            Path(values["RESOLVED"]).samefile(canonical),
            f"expected the canonical sibling {canonical}, resolved {values['RESOLVED']}",
        )
        self.assertEqual(values["TEMP"], "0")

        values = resolve_with({"TIDAS_TOOLS_PATH": str(explicit)})
        self.assertTrue(Path(values["RESOLVED"]).samefile(explicit))

        shutil.rmtree(canonical)
        values = resolve_with({})
        self.assertTrue(
            Path(values["RESOLVED"]).samefile(legacy),
            f"expected the retained legacy sibling {legacy}, resolved {values['RESOLVED']}",
        )

    def prepare_full_verify(self):
        """Small locked source + committed SDK tree; only pnpm phase transport is fake."""
        schema = self.source / "assets/tidas/schemas/process.json"
        schema.parent.mkdir()
        schema.write_text('{"type":"object"}\n')
        lock_path = self.source / "assets/asset-lock.v1.json"
        lock = json.loads(lock_path.read_text())
        lock["entries"].append({"path": "assets/tidas/schemas/process.json", "kind": "json-schema",
                                "sha256": hashlib.sha256(schema.read_bytes()).hexdigest(), "bytes": schema.stat().st_size})
        lock_path.write_text(json.dumps(lock))
        self.git("-C", str(self.source), "add", "-A")
        self.git("-C", str(self.source), "commit", "-qm", "add schema fixture")
        self.pin_sha = self.git("-C", str(self.source), "rev-parse", "HEAD")
        self.git("-C", str(self.source), "push", "-q", str(self.remote), "HEAD:refs/heads/fixture")
        self.sdk = self.root / "sdk"
        scripts = self.sdk / "scripts/ci"
        (scripts / "lib").mkdir(parents=True)
        for name in ("verify-typescript-package.sh", "generate-typescript-sdk.sh", "tidas-tools-assets.mjs",
                     "lib/tidas-tools-source.sh", "lib/typescript-dependencies.sh"):
            shutil.copy2(SCRIPT_ROOT / name, scripts / name)
        # The phase-trace fixture intentionally stubs public-spec resolution:
        # package commands are fake and this test is scoped to the tidas-tools
        # checkout lifetime and generation drift gates.
        (scripts / "lib/tidas-spec-source.sh").write_text("""
RESOLVED_TIDAS_SPEC_ROOT=\"\"
RESOLVED_TIDAS_SPEC_ARCHIVE=\"$REPO_ROOT/fixture-spec.tgz\"
resolve_tidas_spec_source() { :; }
cleanup_tidas_spec_source() { :; }
spec_schema_dir() { printf '%s\\n' \"$REPO_ROOT/fixture-spec/schemas\"; }
spec_methodology_dir() { printf '%s\\n' \"$REPO_ROOT/fixture-spec/methodologies\"; }
spec_asset_root() { printf '%s\\n' \"$REPO_ROOT/fixture-spec\"; }
""")
        for name in ("package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml"):
            shutil.copy2(REPO_ROOT / name, self.sdk / name)
        # The pre-bootstrap automation gate requires Node, not installed package tooling.
        (self.sdk / ".nvmrc").write_text(subprocess.check_output(["node", "--version"], env=self.env, text=True).strip())
        package = self.sdk / "sdks/typescript"
        runtime = package / "src/runtime-assets"
        runtime.mkdir(parents=True)
        shutil.copy2(REPO_ROOT / "sdks/typescript/package.json", package / "package.json")
        shutil.copytree(self.source / "assets/tidas", runtime / "tidas")
        shutil.copy2(lock_path, runtime / "asset-lock.v1.json")
        self.git("init", "-q", str(self.sdk))
        self.git("-C", str(self.sdk), "config", "user.name", "Fixture")
        self.git("-C", str(self.sdk), "config", "user.email", "fixture@example.invalid")
        self.git("-C", str(self.sdk), "config", "commit.gpgsign", "false")
        self.git("-C", str(self.sdk), "add", "-A")
        self.git("-C", str(self.sdk), "commit", "-qm", "sdk fixture")
        self.trace = self.root / "phase-trace"
        self.bin = self.root / "phase-bin"
        self.bin.mkdir()
        pnpm = self.bin / "pnpm"
        pnpm.write_text('''#!/bin/sh
if [ "$1" = --version ]; then printf '%s\\n' 11.24.0; exit 0; fi
printf '%s|%s\\n' "$*" "${TIDAS_TOOLS_PATH:-}" >> "$SDK_PHASE_TRACE"
case "$*" in
  *' run typecheck') phase=typecheck ;;
  *' run generate-types') phase=generate-types ;;
  *) phase=other ;;
esac
if [ "$phase" = "${SDK_FAIL_PHASE:-}" ]; then exit 23; fi
if [ "$phase" = generate-types ] && [ "${SDK_INJECT_DRIFT:-0}" = 1 ]; then
  printf '%s\\n' 'unexpected generation drift' > "$SDK_FIXTURE_ROOT/sdks/typescript/src/drift.ts"
fi
case "$*" in
  *' pack --pack-destination '*) for destination do :; done; printf '%s\\n' fixture > "$destination/fixture.tgz" ;;
esac
''')
        pnpm.chmod(0o755)

    def full_verify_trace(self, *, standalone=False, extra=(), **overrides):
        self.trace.write_text("")
        env = {**self.source_env(), "PATH": str(self.bin) + os.pathsep + self.env["PATH"],
               "TMPDIR": str(self.fixture_tmp), "SDK_PHASE_TRACE": str(self.trace),
               "SDK_FIXTURE_ROOT": str(self.sdk), **overrides}
        script = "generate-typescript-sdk.sh" if standalone else "verify-typescript-package.sh"
        result = subprocess.run(["bash", str(self.sdk / "scripts/ci" / script), *extra],
                                env=env, text=True, capture_output=True)
        calls = [line.split("|", 1) for line in self.trace.read_text().splitlines()]
        self.assertEqual(list(self.fixture_tmp.glob("tidas-tools.*")), [], "owned source must be cleaned on every exit")
        if calls:
            self.assertEqual(len({source for _, source in calls}), 1, "every phase must use the same pinned clone")
            self.assertNotEqual(calls[0][1], str(self.sibling))
        return result, [command for command, _ in calls]

    def test_complete_verify_runs_one_strict_typecheck_and_standalone_keeps_advisory(self):
        self.prepare_full_verify()
        result, calls = self.full_verify_trace()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        expected = ["--filter @tiangong-lca/tidas-sdk --fail-if-no-match run verify-public-rules", "install --frozen-lockfile"] + [
            "--filter @tiangong-lca/tidas-sdk --fail-if-no-match run " + phase
            for phase in ("generate-types", "generate-schemas", "bundle-methodologies", "sync-runtime-assets",
                          "lint", "typecheck", "test", "check:examples", "build")
        ]
        self.assertEqual(calls[:-1], expected)
        self.assertTrue(calls[-1].startswith("--filter @tiangong-lca/tidas-sdk --fail-if-no-match pack --pack-destination "))
        standalone, standalone_calls = self.full_verify_trace(standalone=True)
        self.assertEqual(standalone.returncode, 0, standalone.stderr)
        self.assertEqual(sum(command.endswith(" run typecheck") for command in standalone_calls), 1)
        unknown, calls = self.full_verify_trace(standalone=True, extra=("--unknown",))
        self.assertEqual(unknown.returncode, 2)
        self.assertEqual(calls, [])

    def test_strict_typecheck_failure_stops_later_gates_but_standalone_stays_advisory(self):
        self.prepare_full_verify()
        result, calls = self.full_verify_trace(SDK_FAIL_PHASE="typecheck")
        self.assertEqual(result.returncode, 23, result.stderr)
        self.assertTrue(calls[-1].endswith(" run typecheck"))
        self.assertEqual(sum(command.endswith(" run typecheck") for command in calls), 1)
        for phase in ("test", "check:examples", "build"):
            self.assertFalse(any(command.endswith(" run " + phase) for command in calls))
        self.assertNotIn("pack --dry-run", "\n".join(calls))
        standalone, calls = self.full_verify_trace(standalone=True, SDK_FAIL_PHASE="typecheck")
        self.assertEqual(standalone.returncode, 0, standalone.stderr)
        self.assertIn("Type check failed", standalone.stderr)

    def test_full_verify_retains_generation_pin_and_drift_failures(self):
        self.prepare_full_verify()
        failed_generation, calls = self.full_verify_trace(SDK_FAIL_PHASE="generate-types")
        self.assertNotEqual(failed_generation.returncode, 0)
        self.assertTrue(calls[-1].endswith(" run generate-types"))
        missing_pin, calls = self.full_verify_trace(TIDAS_TOOLS_SHA="0" * 40)
        self.assertNotEqual(missing_pin.returncode, 0)
        self.assertEqual(calls, [])
        drift, calls = self.full_verify_trace(SDK_INJECT_DRIFT="1")
        self.assertNotEqual(drift.returncode, 0)
        self.assertIn("generation introduced uncommitted changes", drift.stderr)
        self.assertFalse(any(command.endswith(" run lint") for command in calls))
        # A real checkout with the correct SHA but stale lock hashes still fails
        # before package-tool execution; no pin-only shortcut is sufficient.
        (self.source / "assets/tidas/schemas/process.json").write_text('{"type":"string"}\n')
        self.git("-C", str(self.source), "add", "-A")
        self.git("-C", str(self.source), "commit", "-qm", "invalid asset hash")
        bad_sha = self.git("-C", str(self.source), "rev-parse", "HEAD")
        self.git("-C", str(self.source), "push", "-q", str(self.remote), "HEAD:refs/heads/fixture")
        bad_lock, calls = self.full_verify_trace(TIDAS_TOOLS_SHA=bad_sha)
        self.assertNotEqual(bad_lock.returncode, 0)
        self.assertEqual(calls, [])


class PrePushDeletionContractTests(unittest.TestCase):
    def test_actual_hook_retains_source_gates_and_classifies_only_branch_deletions(self):
        result = subprocess.run(["sh", str(SCRIPT_ROOT / "test-pre-push.sh")],
                                cwd=REPO_ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
