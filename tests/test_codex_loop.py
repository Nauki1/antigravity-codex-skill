#!/usr/bin/env python3
"""
Unit and integration tests for codex-loop target project resolution and initialization.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

# Add scripts directory to sys.path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from codex_loop import (
    resolve_target_project,
    init_target_project,
    get_current_info,
    AGENTS_TEMPLATE,
)


class TestCodexLoopTargetProject(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="codex_loop_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_resolve_target_project_explicit_valid(self):
        resolved = resolve_target_project(self.test_dir)
        self.assertEqual(resolved, Path(self.test_dir).resolve())

    def test_resolve_target_project_nonexistent(self):
        non_existent = os.path.join(self.test_dir, "does_not_exist_subfolder")
        with self.assertRaises(FileNotFoundError):
            resolve_target_project(non_existent)

    def test_resolve_target_project_file_not_dir(self):
        test_file = Path(self.test_dir) / "some_file.txt"
        test_file.write_text("hello", encoding="utf-8")
        with self.assertRaises(NotADirectoryError):
            resolve_target_project(str(test_file))

    def test_resolve_target_project_default_cwd(self):
        resolved = resolve_target_project(None)
        self.assertTrue(resolved.is_dir())
        self.assertTrue(resolved.exists())

    def test_init_target_project_fresh(self):
        target = Path(self.test_dir)
        success = init_target_project(target_project=str(target), dry_run=False)
        self.assertTrue(success)

        agents_md = target / "AGENTS.md"
        toml_file = target / ".codex-loop.toml"

        self.assertTrue(agents_md.exists())
        self.assertTrue(toml_file.exists())

        agents_content = agents_md.read_text(encoding="utf-8")
        self.assertIn("Dual-Agent Workspace Constitution", agents_content)

        toml_content = toml_file.read_text(encoding="utf-8")
        self.assertIn("headless_agy = true", toml_content)

    def test_init_target_project_dry_run(self):
        target = Path(self.test_dir)
        success = init_target_project(target_project=str(target), dry_run=True)
        self.assertTrue(success)

        agents_md = target / "AGENTS.md"
        toml_file = target / ".codex-loop.toml"

        # In dry run, files must NOT be written
        self.assertFalse(agents_md.exists())
        self.assertFalse(toml_file.exists())
        self.assertFalse((target / ".gitignore").exists())

    def test_init_ignore_patterns_preserve_existing_content_and_are_idempotent(self):
        target = Path(self.test_dir)
        original = b"# Existing project rules\r\nnode_modules/\r\n.review*\r\n"
        ignore = target / ".gitignore"
        ignore.write_bytes(original)
        init_target_project(target_project=target)
        first = ignore.read_bytes()
        self.assertTrue(first.startswith(original))
        self.assertEqual(first.count(b".review*"), 1)
        init_target_project(target_project=target)
        self.assertEqual(ignore.read_bytes(), first)
        if shutil.which("git"):
            subprocess.run(["git", "init", "-q", str(target)], check=True, capture_output=True)
            for name in (".review-scratch/result.txt", ".agents/sessions/session.tmp", ".codex/codex-loop/review-state.json"):
                path = target / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("test fixture", encoding="utf-8")
            checked = subprocess.run(["git", "check-ignore", "--stdin", "-z"], cwd=target, input=b".review-scratch/result.txt\0.agents/sessions/session.tmp\0.codex/codex-loop/review-state.json\0", capture_output=True)
            self.assertEqual(checked.returncode, 0)
            self.assertEqual(len(checked.stdout.rstrip(b"\0").split(b"\0")), 3, checked.stdout + checked.stderr)

    def test_init_upgrades_existing_constitution_without_overwriting_custom_rules(self):
        target = Path(self.test_dir)
        agents = target / "AGENTS.md"
        old = "# Dual-Agent Workspace Constitution (Antigravity & Codex)\nCustom project rule.\n"
        agents.write_text(old, encoding="utf-8")
        init_target_project(target_project=target)
        current = agents.read_text(encoding="utf-8")
        self.assertTrue(current.startswith(old))
        self.assertIn("<!-- codex-loop:phase-checkpoint-v1 -->", current)
        init_target_project(target_project=target)
        self.assertEqual(agents.read_text(encoding="utf-8"), current)

    def test_init_target_project_idempotent(self):
        target = Path(self.test_dir)
        # First init
        init_target_project(target_project=str(target), dry_run=False)
        agents_content_1 = (target / "AGENTS.md").read_text(encoding="utf-8")

        # Second init
        init_target_project(target_project=str(target), dry_run=False)
        agents_content_2 = (target / "AGENTS.md").read_text(encoding="utf-8")

        # Must not duplicate
        self.assertEqual(agents_content_1, agents_content_2)

    def test_init_target_project_append_to_existing_agents(self):
        target = Path(self.test_dir)
        existing_agents = target / "AGENTS.md"
        existing_agents.write_text("# My Existing Custom Rules\n- Rule 1\n", encoding="utf-8")

        init_target_project(target_project=str(target), dry_run=False)
        updated_content = existing_agents.read_text(encoding="utf-8")

        self.assertTrue(updated_content.startswith("# My Existing Custom Rules"))
        self.assertIn("Dual-Agent Workspace Constitution", updated_content)

    def test_get_current_info_with_target(self):
        target = Path(self.test_dir)
        info = get_current_info(target_project=str(target))
        self.assertIn("target_project", info)
        self.assertEqual(info["target_project"]["root"], str(target.resolve()))
        self.assertFalse(info["target_project"]["agents_md_exists"])
        self.assertFalse(info["target_project"]["codex_loop_toml_exists"])

    def test_argument_parsing_project_precedence(self):
        from codex_loop import build_parser

        parser = build_parser()
        # 1. Preceding subcommand
        args_pre = parser.parse_args(["--project", self.test_dir, "exec-agy"])
        self.assertEqual(getattr(args_pre, "project", None), self.test_dir)

        # 2. Succeeding subcommand
        args_post = parser.parse_args(["exec-agy", "--project", self.test_dir])
        self.assertEqual(getattr(args_post, "project", None), self.test_dir)

        # 3. Omitted
        args_none = parser.parse_args(["exec-agy"])
        self.assertIsNone(getattr(args_none, "project", None))

        # 4. Init subcommand with preceding --project
        args_init = parser.parse_args(["--project", self.test_dir, "init", "--dry-run"])
        self.assertEqual(getattr(args_init, "project", None), self.test_dir)
        self.assertTrue(args_init.dry_run)


if __name__ == "__main__":
    unittest.main()
