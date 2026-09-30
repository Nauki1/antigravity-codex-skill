"""Offline regression tests for review decisions, CLI scopes, and exit codes."""

import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import codex_loop


class TestReview(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="review 中文 ")
        self.addCleanup(self.temp.cleanup)
        self.target = self.temp.name
        self.runner = self.enterContext(patch.object(codex_loop.subprocess, "run"))
        self.enterContext(patch.object(codex_loop, "get_current_info", return_value={"active_model": "test-model"}))
        self.enterContext(patch.object(codex_loop, "CODEX_BIN", "test-codex"))
        self.enterContext(contextlib.redirect_stdout(io.StringIO()))
        self.stderr = self.enterContext(contextlib.redirect_stderr(io.StringIO()))

    def response(self, output, returncode=0, stderr=""):
        def run(args, **kwargs):
            if args[0] == "git":
                return subprocess.CompletedProcess(args, 0, "a" * 40 + "\n", "")
            if "--output-last-message" in args:
                path = Path(args[args.index("--output-last-message") + 1])
                with path.open("w", encoding="utf-8", newline="") as stream:
                    stream.write(output)
            return subprocess.CompletedProcess(args, returncode, "Rendered review report.\n", stderr)
        self.runner.side_effect = run

    def review(self, **kwargs):
        return codex_loop.run_review(target_project=self.target, **kwargs)

    def invoke(self, *args):
        with self.assertRaises(SystemExit) as caught:
            codex_loop.main(["review", "--project", self.target, *args])
        return caught.exception.code

    def test_explicit_approval_with_crlf_and_trailing_blank_lines(self):
        output = json.dumps(json.loads(self.native_report()), indent=2).replace("\n", "\r\n") + "\r\n\r\n"
        self.response(output)
        self.assertTrue(self.review()[0])

    def test_negative_quoted_unknown_and_incomplete_outputs_never_approve(self):
        outputs = [
            "NOT APPROVED", "NEEDS_FIX", "lgtm", "looks good", "no regressions", "",
            "No actionable regressions were identified.",
            'The sample says "APPROVED".', '> APPROVED', '`APPROVED`',
            '"APPROVED"', '    APPROVED', '```text\nAPPROVED\n```',
            '```text\nAPPROVED', '~~~text\nAPPROVED',
            'APPROVED\nNEEDS_FIX', 'NEEDS_FIX\nAPPROVED',
            'NOT APPROVED\nAPPROVED', 'APPROVED\nAPPROVED',
            'Example: APPROVED\nAPPROVED',
            '[P1] Broken call remains.\nAPPROVED',
            '> Quoted example\nAPPROVED', '<pre>\nAPPROVED',
            '<blockquote>\nAPPROVED', '<code>\nAPPROVED', '<!--\nAPPROVED',
        ]
        for output in outputs:
            with self.subTest(output=output):
                self.response(output)
                try:
                    approved, _ = self.review()
                except codex_loop.ReviewError:
                    approved = False
                self.assertFalse(approved)

    def test_explanations_with_code_and_labels_do_not_change_verdict(self):
        for output in (
            '```python\nprint(1)\n```\n\nNo findings.\nAPPROVED',
            '> Background\n\nNo findings.\nAPPROVED',
            '<code>example</code>\n\nNo findings.\nAPPROVED',
            'The parser handles `<pre>` correctly.\nAPPROVED',
            '```html\n<pre>\n```\nNo findings.\nAPPROVED',
            '> Background\n# Review\nNo findings.\nAPPROVED',
            '```text\n> Example\n```\nNo findings.\nAPPROVED',
            'No findings; the `[P1]` fixture is handled correctly.\nAPPROVED',
            '```text\n[P1] example\n```\nNo findings.\nAPPROVED',
        ):
            with self.subTest(output=output):
                self.response(self.native_report(reason=output))
                self.assertTrue(self.review()[0])

    def test_nonzero_process_with_approval_is_execution_failure(self):
        self.response("APPROVED", returncode=7, stderr="service failed")
        self.assertEqual(self.invoke(), 1)
        self.assertIn("service failed", self.stderr.getvalue())

    def test_executable_missing_is_execution_failure(self):
        self.runner.side_effect = FileNotFoundError("missing CLI")
        self.assertEqual(self.invoke(), 1)

    def test_unknown_output_is_invalid_result(self):
        for output in ("", "lgtm", "NOT APPROVED", "APPROVED\nNEEDS_FIX"):
            with self.subTest(output=output):
                self.response(output)
                self.assertEqual(self.invoke(), 1)

    def test_valid_rejection_exits_two(self):
        self.response(self.native_report(overall_correctness="patch is incorrect", reason="Fix the argument conflict."))
        self.assertEqual(self.invoke(), 2)

    def test_valid_approval_exits_zero(self):
        self.response(self.native_report())
        self.assertEqual(self.invoke(), 0)

    def test_rendered_review_envelope_is_accepted(self):
        self.response(json.dumps({
            "protocol": "codex-loop-review-v1", "review_complete": True,
            "findings_count": 0, "overall_correctness": "patch is correct",
            "reason": "No actionable regressions found after reviewing the changes.",
        }))
        self.assertEqual(self.invoke(), 0)

    def test_default_review_uses_custom_uncommitted_scope_and_target_cwd(self):
        self.response(self.native_report())
        self.review()
        args = self.runner.call_args.args[0]
        self.assertNotIn("--uncommitted", args)
        self.assertNotIn("--base", args)
        self.assertIn("staged, unstaged, and untracked", args[-1])
        self.assertIn(codex_loop.REVIEW_PROTOCOL, args[-1])
        self.assertEqual(args[-2], "--")
        self.assertEqual(self.runner.call_args.kwargs["cwd"], str(Path(self.target).resolve()))
        self.assertEqual(self.runner.call_args.kwargs["stdin"], subprocess.DEVNULL)

    def test_base_review_pins_merge_base_without_conflicting_flags(self):
        self.response(self.native_report())
        self.review(base="origin/main")
        args = self.runner.call_args.args[0]
        self.assertNotIn("--uncommitted", args)
        self.assertNotIn("--base", args)
        merge_call = self.runner.call_args_list[0]
        self.assertEqual(merge_call.args[0], ["git", "merge-base", "--", "HEAD", "origin/main"])
        self.assertEqual(merge_call.kwargs["cwd"], str(Path(self.target).resolve()))
        self.assertIn("a" * 40, args[-1])
        self.assertIn('"origin/main"', args[-1])
        self.assertEqual(args[:3], ["test-codex", "exec", "review"])
        self.assertEqual(args[-4:-2], ["-c", 'model="test-model"'])
        self.assertIn("--output-last-message", args)
        self.assertIn(codex_loop.REVIEW_PROTOCOL, args[-1])

    def test_custom_instructions_use_prompt_without_target_flags(self):
        self.response(self.native_report())
        self.review(instructions="Review Unicode path handling.")
        args = self.runner.call_args.args[0]
        self.assertNotIn("--uncommitted", args)
        self.assertNotIn("--base", args)
        self.assertIn("Review Unicode path handling.", args[-1])
        self.assertIn("APPROVED", args[-1])
        self.assertIn("NEEDS_FIX", args[-1])
        self.assertEqual(args[-2], "--")

    def test_conflicting_scope_and_prompt_rejected_before_launch(self):
        with self.assertRaises(codex_loop.ReviewError):
            self.review(base="main", instructions="Review auth.")
        self.runner.assert_not_called()

    def test_cli_conflicting_arguments_rejected_before_launch(self):
        self.assertEqual(self.invoke("--base", "main", "--instructions", "Review auth."), 2)
        self.runner.assert_not_called()

    def test_raw_result_preserved(self):
        output = self.native_report() + "\r\n\r\n"
        self.response(output)
        self.assertEqual(self.review()[1], output)
        args = self.runner.call_args.args[0]
        self.assertFalse(Path(args[args.index("--output-last-message") + 1]).exists())

    def test_result_file_is_cleaned_after_process_failure(self):
        self.response("partial result", returncode=1)
        self.assertEqual(self.invoke(), 1)
        args = self.runner.call_args.args[0]
        self.assertFalse(Path(args[args.index("--output-last-message") + 1]).exists())

    def native_report(self, **changes):
        report = {
            "protocol": "codex-loop-review-v1",
            "review_complete": True,
            "findings_count": 0,
            "overall_correctness": "patch is correct",
            "reason": "The change fixes the review gate without actionable regressions.",
        }
        report.update(changes)
        return json.dumps(report)

    def test_native_structured_approval_and_raw_output(self):
        output = self.native_report()
        self.response(output)
        approved, raw = self.review()
        self.assertTrue(approved)
        self.assertEqual(raw, output)
        self.assertEqual(self.invoke(), 0)

    def test_native_structured_incorrect_patch_requires_fix(self):
        self.response(self.native_report(overall_correctness="patch is incorrect"))
        self.assertEqual(self.invoke(), 2)

    def test_native_rendered_findings_never_approve(self):
        for suffix in ("", "\n\nFull review comments:\n\n- [P1] Fix the call — runner.py:1\n  The flags conflict."):
            for verdict in ("patch is correct", "patch is incorrect"):
                with self.subTest(verdict=verdict, suffix=suffix):
                    self.response(self.native_report(findings_count=1, overall_correctness=verdict) + suffix)
                    self.assertEqual(self.invoke(), 2)

    def test_extra_rendered_findings_or_verdicts_after_zero_findings_fail_closed(self):
        for suffix in ('\nFull review comments:\n- [P1] Fix the call', '\nAPPROVED', '\nNEEDS_FIX', '\n{}'):
            with self.subTest(suffix=suffix):
                self.response(self.native_report() + suffix)
                self.assertEqual(self.invoke(), 1)

    def test_invalid_base_fails_before_review_launch(self):
        self.runner.side_effect = None
        for code, output in ((1, ""), (0, "not a revision")):
            with self.subTest(code=code, output=output):
                self.runner.reset_mock()
                self.runner.return_value = subprocess.CompletedProcess([], code, output, "bad ref")
                self.assertEqual(self.invoke("--base=-invalid"), 1)
                self.assertEqual(self.runner.call_count, 1)
                self.assertEqual(self.runner.call_args.args[0][-2:], ["HEAD", "-invalid"])

    def test_empty_scope_is_rejected_before_launch(self):
        for kwargs in ({"base": " "}, {"instructions": ""}):
            with self.subTest(kwargs=kwargs), self.assertRaises(codex_loop.ReviewError):
                self.review(**kwargs)
        self.runner.assert_not_called()

    def test_missing_raw_report_never_uses_rendered_approval(self):
        self.runner.side_effect = None
        self.runner.return_value = subprocess.CompletedProcess([], 0, "APPROVED", "")
        self.assertEqual(self.invoke(), 1)

    def test_raw_report_invalid_utf8_is_execution_failure(self):
        def run(args, **kwargs):
            Path(args[args.index("--output-last-message") + 1]).write_bytes(b"\xffAPPROVED")
            return subprocess.CompletedProcess(args, 0, "APPROVED", "")
        self.runner.side_effect = run
        self.assertEqual(self.invoke(), 1)

    def test_invalid_or_incomplete_native_reports_fail_closed(self):
        valid = json.loads(self.native_report())
        outputs = [
            '{}', '{"findings": []}', self.native_report(findings_count=None),
            self.native_report(findings_count=True), self.native_report(findings_count=-1),
            self.native_report(findings_count=0.0), self.native_report(overall_correctness="APPROVED"),
            self.native_report(review_complete=False), self.native_report(review_complete="true"),
            self.native_report(protocol="wrong"), self.native_report(reason=""),
            self.native_report(reason=None),
            self.native_report(extra_verdict="NEEDS_FIX"),
            self.native_report()[:-1],
            self.native_report() + '\nAPPROVED',
            self.native_report().replace('"findings_count": 0', '"findings_count": 1, "findings_count": 0'),
        ]
        for key in valid:
            outputs.append(json.dumps({k: v for k, v in valid.items() if k != key}))
        for output in outputs:
            with self.subTest(output=output):
                self.response(output)
                self.assertEqual(self.invoke(), 1)


if __name__ == "__main__":
    unittest.main()
