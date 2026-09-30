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
        self.response(self.native_report(findings=[self.finding()], overall_correctness="patch is incorrect", reason="Fix the argument conflict."))
        self.assertEqual(self.invoke(), 2)

    def test_valid_approval_exits_zero(self):
        self.response(self.native_report())
        self.assertEqual(self.invoke(), 0)

    def test_rendered_review_envelope_is_accepted(self):
        self.response(json.dumps({
            "protocol": "codex-loop-review-v3", "review_complete": True, "findings": [],
            "findings_count": 0, "overall_correctness": "patch is correct",
            "reason": "No actionable regressions found after reviewing the changes.",
            "acceptance_met": True, "advisories": [], "uncertainties": [],
        }))
        self.assertEqual(self.invoke(), 0)

    def test_default_review_uses_custom_uncommitted_scope_and_target_cwd(self):
        self.response(self.native_report())
        self.review()
        args = self.runner.call_args.args[0]
        self.assertNotIn("--uncommitted", args)
        self.assertNotIn("--base", args)
        self.assertIn("staged, unstaged, and untracked", self.runner.call_args.kwargs["input"])
        self.assertIn(codex_loop.REVIEW_PROTOCOL, self.runner.call_args.kwargs["input"])
        self.assertEqual(args[-2], "--")
        self.assertEqual(args[-1], "-")
        self.assertEqual(self.runner.call_args.kwargs["cwd"], str(Path(self.target).resolve()))
        self.assertNotIn("stdin", self.runner.call_args.kwargs)

    def test_base_review_pins_merge_base_without_conflicting_flags(self):
        self.response(self.native_report())
        self.review(base="origin/main")
        args = self.runner.call_args.args[0]
        self.assertNotIn("--uncommitted", args)
        self.assertNotIn("--base", args)
        merge_call = self.runner.call_args_list[0]
        self.assertEqual(merge_call.args[0], ["git", "merge-base", "--", "HEAD", "origin/main"])
        self.assertEqual(merge_call.kwargs["cwd"], str(Path(self.target).resolve()))
        self.assertIn("a" * 40, self.runner.call_args.kwargs["input"])
        self.assertIn('"origin/main"', self.runner.call_args.kwargs["input"])
        self.assertEqual(args[:3], ["test-codex", "exec", "review"])
        self.assertEqual(args[-4:-2], ["-c", 'model="test-model"'])
        self.assertIn("--output-last-message", args)
        self.assertIn(codex_loop.REVIEW_PROTOCOL, self.runner.call_args.kwargs["input"])

    def test_custom_instructions_use_prompt_without_target_flags(self):
        self.response(self.native_report())
        self.review(instructions="Review Unicode path handling.")
        args = self.runner.call_args.args[0]
        self.assertNotIn("--uncommitted", args)
        self.assertNotIn("--base", args)
        self.assertIn("Review Unicode path handling.", self.runner.call_args.kwargs["input"])
        self.assertIn("APPROVED", self.runner.call_args.kwargs["input"])
        self.assertIn("NEEDS_FIX", self.runner.call_args.kwargs["input"])
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
            "protocol": "codex-loop-review-v3",
            "review_complete": True,
            "findings_count": 0,
            "findings": [],
            "overall_correctness": "patch is correct",
            "reason": "The change fixes the review gate without actionable regressions.",
            "acceptance_met": True, "advisories": [], "uncertainties": [],
        }
        report.update(changes)
        if "adjudications" in changes and "history" not in changes:
            report["history"] = [{key: self.finding(id=item["finding_id"])[key] for key in ("id", "title", "location", "trigger")} for item in changes["adjudications"]]
        if "findings" in changes and "findings_count" not in changes and isinstance(changes["findings"], list):
            report["findings_count"] = len(changes["findings"])
        output = json.dumps(report)
        if isinstance(report["findings"], list) and report["findings"]:
            output += "\n\nReview comment:\n\n" + "\n".join(
                f"- {finding.get('title', '')} — {finding.get('location', '')}\n  Verified finding."
                for finding in report["findings"] if isinstance(finding, dict)
            )
        return output

    def finding(self, **changes):
        finding = {
            "id": "F1", "title": "Division by zero", "location": "average.py:2",
            "trigger": "average([1, 2])", "expected": "Returns 1.5",
            "actual": "Raises ZeroDivisionError", "impact": "Supported input cannot be processed",
            "evidence": "The reachable return expression divides sum(values) by literal zero.",
            "verified": True,
        }
        finding.update(changes)
        return finding

    def test_native_structured_approval_and_raw_output(self):
        output = self.native_report()
        self.response(output)
        approved, raw = self.review()
        self.assertTrue(approved)
        self.assertEqual(raw, output)
        self.assertEqual(self.invoke(), 0)

    def test_native_structured_incorrect_patch_requires_fix(self):
        self.response(self.native_report(findings=[self.finding()], overall_correctness="patch is incorrect"))
        self.assertEqual(self.invoke(), 2)

    def test_native_rendered_findings_never_approve(self):
        for header in ("Review comment:", "Full review comments:"):
            for verdict in ("patch is correct", "patch is incorrect"):
                with self.subTest(verdict=verdict, header=header):
                    self.response(self.native_report(findings=[self.finding()], overall_correctness=verdict).replace("Review comment:", header))
                    self.assertEqual(self.invoke(), 2)

    def test_native_comments_must_correspond_to_evidence_records(self):
        output = self.native_report(findings=[self.finding()])
        for malformed in (
            output + "\n- Extra native finding — other.py:2\n  No evidence record.",
            output.replace("- Division by zero —", "- Different native finding —"),
            output.split("\n\nReview comment:")[0],
            output + "\nAPPROVED",
        ):
            with self.subTest(output=malformed):
                self.response(malformed)
                self.assertEqual(self.invoke(), 1)

    def test_native_single_line_ranges_match_equivalent_evidence_location(self):
        output = self.native_report(findings=[self.finding()])
        self.response(output.replace("— average.py:2\n", "— average.py:2-2\n"))
        self.assertEqual(self.invoke(), 2)
        self.response(output.replace("— average.py:2\n", "— average.py:2-3\n"))
        self.assertEqual(self.invoke(), 1)

    def test_unsubstantiated_incorrect_verdict_remains_pending(self):
        self.response(self.native_report(overall_correctness="patch is incorrect"))
        self.assertEqual(self.invoke(), 1)

    def test_findings_require_complete_verified_evidence(self):
        records = [self.finding(verified=False), self.finding(verified="true"), self.finding(evidence=" "), self.finding(trigger=None)]
        for key in self.finding():
            records.append({k: v for k, v in self.finding().items() if k != key})
        for finding in records:
            with self.subTest(finding=finding):
                self.response(self.native_report(findings=[finding]))
                self.assertEqual(self.invoke(), 1)

    def test_duplicate_finding_ids_and_inconsistent_counts_fail_closed(self):
        for output in (
            self.native_report(findings=[self.finding(), self.finding()]),
            self.native_report(findings=[self.finding()], findings_count=0),
            self.native_report(findings=None),
        ):
            with self.subTest(output=output):
                self.response(output)
                self.assertEqual(self.invoke(), 1)

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

    def test_default_task_is_read_from_target_project(self):
        task = Path(self.target) / "docs/task.md"
        task.parent.mkdir()
        task.write_text("Acceptance: support nonempty integer lists.\nNon-goal: float support.", encoding="utf-8")
        self.response(self.native_report())
        self.review()
        prompt = self.runner.call_args.kwargs["input"]
        self.assertIn(task.read_bytes().decode("utf-8"), prompt)
        self.assertIn(str(task), prompt)
        self.assertIn("SHA-256", prompt)

    def test_explicit_task_path_is_relative_to_target(self):
        task = Path(self.target) / "验收 标准.md"
        task.write_text("验收：原有功能仍然可用。", encoding="utf-8")
        self.response(self.native_report())
        self.assertEqual(self.invoke("--task", task.name), 0)
        self.assertIn("原有功能仍然可用", self.runner.call_args.kwargs["input"])

    def test_missing_empty_and_invalid_utf8_tasks_fail_before_launch(self):
        task = Path(self.target) / "task.md"
        for content in (None, b" \n", b"\xef\xbb\xbf \n", b"\xff"):
            with self.subTest(content=content):
                if content is not None:
                    task.write_bytes(content)
                self.assertEqual(self.invoke("--task", task.name), 1)
                self.runner.assert_not_called()

    def test_task_changed_during_review_invalidates_approval(self):
        task = Path(self.target) / "task.md"
        task.write_text("Acceptance: initial standard.", encoding="utf-8")
        self.response(self.native_report())
        original_run = self.runner.side_effect
        def mutate(args, **kwargs):
            result = original_run(args, **kwargs)
            task.write_text("Acceptance: expanded standard.", encoding="utf-8")
            return result
        self.runner.side_effect = mutate
        self.assertEqual(self.invoke("--task", task.name), 1)
        self.assertIn("发生变化", self.stderr.getvalue())

    def test_implicit_task_created_during_review_invalidates_approval(self):
        task = Path(self.target) / "docs/task.md"
        self.response(self.native_report())
        original_run = self.runner.side_effect
        def mutate(args, **kwargs):
            result = original_run(args, **kwargs)
            task.parent.mkdir()
            task.write_text("New acceptance criteria.", encoding="utf-8")
            return result
        self.runner.side_effect = mutate
        self.assertEqual(self.invoke(), 1)

    def test_large_task_does_not_expand_windows_command_line(self):
        task = Path(self.target) / "task.md"
        content = "验收：" + "x" * 40000
        task.write_text(content, encoding="utf-8")
        self.response(self.native_report())
        self.assertEqual(self.invoke("--task", task.name), 0)
        self.assertLess(len(subprocess.list2cmdline(self.runner.call_args.args[0])), 4096)
        self.assertIn(content, self.runner.call_args.kwargs["input"])

    def discussion(self, replies=None):
        previous = Path(self.target) / "previous.txt"
        response = Path(self.target) / "response.json"
        previous.write_text(self.native_report(findings=[self.finding()], overall_correctness="patch is incorrect"), encoding="utf-8")
        response.write_text(json.dumps({"responses": replies if replies is not None else [{"finding_id": "F1", "position": "disputed", "reason": "The reported path is unreachable.", "evidence": "A guard rejects empty input before the return expression."}]}), encoding="utf-8")
        return previous, response

    def decision(self, **changes):
        decision = {"finding_id": "F1", "decision": "closed", "reason": "Checked the implementer evidence.", "evidence": "The code path and regression test rule out the claim."}
        decision.update(changes)
        return decision

    def test_verified_rebuttal_can_close_finding_and_save_raw_report(self):
        previous, response = self.discussion()
        output = self.native_report(adjudications=[self.decision()])
        self.response(output)
        saved = Path(self.target) / "reviews/result.txt"
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name, "--out", str(saved)), 0)
        self.assertEqual(saved.read_text(encoding="utf-8"), output)
        self.assertIn("The reported path is unreachable", self.runner.call_args.kwargs["input"])

    def test_confirmed_finding_after_rebuttal_requires_fix(self):
        previous, response = self.discussion()
        self.response(self.native_report(findings=[self.finding()], adjudications=[self.decision(decision="confirmed")]))
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 2)

    def test_unresolved_dispute_stays_pending_and_is_saved(self):
        previous, response = self.discussion()
        output = self.native_report(adjudications=[self.decision(decision="needs_human")])
        self.response(output)
        saved = Path(self.target) / "pending.txt"
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name, "--out", saved.name), 1)
        self.assertEqual(saved.read_text(encoding="utf-8"), output)

    def test_unanswered_response_and_unexpected_decision_fail_closed(self):
        previous, response = self.discussion()
        for decisions in ([], [self.decision(finding_id="unknown")]):
            with self.subTest(decisions=decisions):
                self.response(self.native_report(adjudications=decisions))
                self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 1)

    def test_malformed_unknown_and_duplicate_responses_stop_before_launch(self):
        for replies in ([], [{"finding_id": "F1"}], [{"finding_id": "F9", "position": "disputed", "reason": "reason", "evidence": "proof"}], [{"finding_id": "F1", "position": "disputed", "reason": "reason", "evidence": ""}]):
            with self.subTest(replies=replies):
                previous, response = self.discussion(replies)
                self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 1)
                self.runner.assert_not_called()
        previous, response = self.discussion()
        data = json.loads(response.read_text(encoding="utf-8"))
        data["responses"] *= 2
        response.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 1)
        self.runner.assert_not_called()

    def test_response_requires_previous_review_and_output_cannot_overwrite_inputs(self):
        previous, response = self.discussion()
        self.assertEqual(self.invoke("--response", response.name), 1)
        self.assertEqual(self.invoke("--previous-review", previous.name, "--out", previous.name), 1)
        self.assertEqual(self.invoke("--out", "docs/task.md"), 1)
        self.runner.assert_not_called()

    def test_contradictory_or_unsubstantiated_adjudications_are_invalid(self):
        outputs = [
            self.native_report(adjudications=[self.decision(evidence="")]),
            self.native_report(adjudications=[self.decision(), self.decision()]),
            self.native_report(adjudications=[self.decision(decision="confirmed")]),
            self.native_report(findings=[self.finding()], adjudications=[self.decision()]),
        ]
        for output in outputs:
            with self.subTest(output=output):
                self.response(output)
                self.assertEqual(self.invoke(), 1)

    def test_response_changed_during_review_invalidates_adjudication(self):
        previous, response = self.discussion()
        self.response(self.native_report(adjudications=[self.decision()]))
        original_run = self.runner.side_effect
        def mutate(args, **kwargs):
            result = original_run(args, **kwargs)
            response.write_text("{}", encoding="utf-8")
            return result
        self.runner.side_effect = mutate
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 1)

    def test_prior_unresolved_dispute_cannot_disappear_without_response(self):
        previous = Path(self.target) / "pending.txt"
        previous.write_text(self.native_report(adjudications=[self.decision(decision="needs_human")]), encoding="utf-8")
        self.response(self.native_report())
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)
        self.response(self.native_report(adjudications=[self.decision(decision="needs_human")]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)
        self.assertIn("需用户决定", self.stderr.getvalue())

    def test_followup_requires_decisions_for_every_prior_finding(self):
        previous, _ = self.discussion()
        self.response(self.native_report())
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)
        self.response(self.native_report(adjudications=[self.decision()]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 0)
        self.assertIn(codex_loop.REVIEW_FOLLOWUP, self.runner.call_args.kwargs["input"])

    def test_closed_history_cannot_disappear_or_reopen_without_new_evidence(self):
        previous = Path(self.target) / "closed.txt"
        previous.write_text(self.native_report(adjudications=[self.decision()]), encoding="utf-8")
        for output in (
            self.native_report(),
            self.native_report(findings=[self.finding()], adjudications=[self.decision(decision="confirmed")]),
            self.native_report(findings=[self.finding()], adjudications=[self.decision(decision="reopened")]),
            self.native_report(findings=[self.finding()], adjudications=[self.decision(decision="reopened", new_evidence=self.decision()["evidence"].upper())]),
        ):
            self.response(output)
            self.assertEqual(self.invoke("--previous-review", previous.name), 1)
        self.response(self.native_report(adjudications=[self.decision()]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 0)

    def test_new_verified_evidence_can_reopen_closed_problem(self):
        previous = Path(self.target) / "closed.txt"
        previous.write_text(self.native_report(adjudications=[self.decision()]), encoding="utf-8")
        self.response(self.native_report(findings=[self.finding()], adjudications=[self.decision(decision="reopened", new_evidence="A later change removed the previously tested guard.")]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 2)

    def test_reopened_decision_requires_a_prior_closed_problem(self):
        previous, _ = self.discussion()
        self.response(self.native_report(findings=[self.finding()], adjudications=[self.decision(decision="reopened", new_evidence="new proof")]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)

    def test_followup_allows_new_regression_but_retains_old_issue_id(self):
        previous, _ = self.discussion()
        new = self.finding(id="F2", title="New regression", location="other.py:3", trigger="Another supported input")
        self.response(self.native_report(findings=[new], adjudications=[self.decision()]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 2)
        self.response(self.native_report(findings=[self.finding(id="F2")], adjudications=[self.decision()]))
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)

    def test_closed_claim_identity_survives_consecutive_followups(self):
        previous, _ = self.discussion()
        closed = Path(self.target) / "closed.txt"
        self.response(self.native_report(adjudications=[self.decision()]))
        self.assertEqual(self.invoke("--previous-review", previous.name, "--out", closed.name), 0)
        self.response(self.native_report(findings=[self.finding(id="F2")], adjudications=[self.decision()]))
        self.assertEqual(self.invoke("--previous-review", closed.name), 1)

    def test_shifted_current_claim_cannot_be_reassigned(self):
        previous, _ = self.discussion()
        previous.write_text(self.native_report(findings=[self.finding(location="average.py:8")], adjudications=[self.decision(decision="confirmed")]), encoding="utf-8")
        prior = codex_loop.parse_review_report(previous.read_text(encoding="utf-8"))
        self.response(self.native_report(findings=[self.finding(id="F2", location="average.py:8")], adjudications=[self.decision()], history=codex_loop.review_history(prior)))
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)

    def test_shifted_identity_is_preserved_after_closure(self):
        previous, _ = self.discussion()
        previous.write_text(self.native_report(findings=[self.finding(location="average.py:8")], adjudications=[self.decision(decision="confirmed")]), encoding="utf-8")
        history = [{key: self.finding(location=location)[key] for key in ("id", "title", "location", "trigger")} for location in ("average.py:2", "average.py:8")]
        closed = Path(self.target) / "closed.txt"
        self.response(self.native_report(adjudications=[self.decision()], history=history))
        self.assertEqual(self.invoke("--previous-review", previous.name, "--out", closed.name), 0)
        self.response(self.native_report(findings=[self.finding(id="F2", location="average.py:8")], adjudications=[self.decision()], history=history))
        self.assertEqual(self.invoke("--previous-review", closed.name), 1)

    def test_equivalent_claim_locations_cannot_bypass_id_retention(self):
        previous, _ = self.discussion()
        for original, updated in (("average.py:2", "average.py:2-2"), ("D:\\app\\average.py:2", "D:/app/average.py:2-2")):
            previous.write_text(self.native_report(findings=[self.finding(location=original)]), encoding="utf-8")
            history = [{key: self.finding(location=original)[key] for key in ("id", "title", "location", "trigger")}]
            self.response(self.native_report(findings=[self.finding(id="F2", location=updated)], adjudications=[self.decision()], history=history))
            self.assertEqual(self.invoke("--previous-review", previous.name), 1)

    def test_missing_modified_and_legacy_closed_identity_history_is_pending(self):
        previous, _ = self.discussion()
        for history in ([], [{"id": "F1", "title": "changed", "location": "average.py:2", "trigger": "average([1, 2])"}]):
            self.response(self.native_report(adjudications=[self.decision()], history=history))
            self.assertEqual(self.invoke("--previous-review", previous.name), 1)
        previous.write_text(self.native_report(adjudications=[self.decision()], history=[]), encoding="utf-8")
        self.runner.reset_mock()
        self.assertEqual(self.invoke("--previous-review", previous.name), 1)
        self.runner.assert_not_called()

    def test_partial_response_cannot_drop_another_unresolved_dispute(self):
        previous, response = self.discussion([{"finding_id": "F2", "position": "fixed", "reason": "Fixed", "evidence": "Passing test"}])
        previous.write_text(self.native_report(findings=[self.finding(id="F2")], adjudications=[self.decision(decision="needs_human"), self.decision(finding_id="F2", decision="confirmed")]), encoding="utf-8")
        self.response(self.native_report(adjudications=[self.decision(finding_id="F2")]))
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 1)
        self.response(self.native_report(adjudications=[self.decision(finding_id="F2"), self.decision(decision="needs_human")]))
        self.assertEqual(self.invoke("--previous-review", previous.name, "--response", response.name), 1)
        self.assertIn("需用户决定", self.stderr.getvalue())

    def test_missing_raw_report_never_uses_rendered_approval(self):
        self.runner.side_effect = None
        self.runner.return_value = subprocess.CompletedProcess([], 0, "APPROVED", "")
        self.assertEqual(self.invoke(), 1)

    def test_advisories_do_not_block_accepted_work(self):
        self.response(self.native_report(advisories=["Optional naming improvement."]))
        self.assertEqual(self.invoke(), 0)

    def test_unmet_acceptance_or_uncertainty_never_approves_or_assigns_blind_repairs(self):
        for report in (self.native_report(acceptance_met=False), self.native_report(uncertainties=["Need a runtime trace to establish this potential defect."])):
            self.response(report)
            self.assertEqual(self.invoke(), 1)

    def test_legacy_reports_are_readable_history_but_cannot_be_live_approvals(self):
        legacy = json.loads(self.native_report())
        legacy["protocol"] = "codex-loop-review-v2"
        for key in ("acceptance_met", "advisories", "uncertainties"):
            del legacy[key]
        self.assertEqual(codex_loop.parse_review_report(json.dumps(legacy))["protocol"], "codex-loop-review-v2")
        self.response(json.dumps(legacy))
        self.assertEqual(self.invoke(), 1)
        previous = Path(self.target) / "legacy.txt"
        previous.write_text(json.dumps(legacy), encoding="utf-8")
        self.response(self.native_report())
        self.assertEqual(self.invoke("--previous-review", previous.name), 0)

    def test_acceptance_and_advisory_fields_require_valid_types(self):
        for changes in ({"acceptance_met": "true"}, {"advisories": [""]}, {"advisories": "none"}, {"uncertainties": [False]}):
            self.response(self.native_report(**changes))
            self.assertEqual(self.invoke(), 1)

    def invoke_fix(self, report, *args):
        with self.assertRaises(SystemExit) as caught:
            codex_loop.main(["fix", "--project", self.target, "--review", str(report), *args])
        return caught.exception.code

    def save_fix_review(self, **changes):
        task = Path(self.target) / "docs/task.md"
        task.parent.mkdir(exist_ok=True)
        if not task.exists():
            task.write_text("Acceptance: average([1, 2]) returns 1.5.", encoding="utf-8")
        report = Path(self.target) / "review.txt"
        data = {"findings": [self.finding()], "overall_correctness": "patch is incorrect"}
        data.update(changes)
        self.response(self.native_report(**data))
        self.invoke("--out", str(report))
        return report

    def test_fix_budget_persists_and_stops_at_two_attempts(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        for _ in range(2):
            self.assertEqual(self.invoke_fix(self.save_fix_review()), 0)
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 3)
        self.assertEqual(agy.call_count, 2)
        state = json.loads(next((Path(self.target) / ".codex/codex-loop").glob("fix-*.json")).read_text(encoding="utf-8"))
        self.assertEqual(state["attempts"], 2)
        self.assertEqual(len(set(state["used_reviews"])), 2)
        self.assertIn("advisories", agy.call_args.kwargs["prompt"])

    def test_failed_attempt_counts_and_same_review_cannot_be_reused(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=False))
        report = self.save_fix_review()
        self.assertEqual(self.invoke_fix(report), 1)
        self.assertEqual(self.invoke_fix(report), 1)
        self.assertEqual(agy.call_count, 1)
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 1)
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 3)
        self.assertEqual(agy.call_count, 2)

    def test_raising_configuration_cannot_expand_existing_budget(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        config = Path(self.target) / ".codex-loop.toml"
        config.write_text("[collaboration]\nmax_fix_rounds = 1\n", encoding="utf-8")
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 0)
        config.write_text("[collaboration]\nmax_fix_rounds = 9\n", encoding="utf-8")
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 3)
        self.assertEqual(agy.call_count, 1)

    def test_pending_and_approved_reports_do_not_launch_repairs(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        approved = self.save_fix_review(findings=[], overall_correctness="patch is correct", advisories=["Optional optimization"])
        self.assertEqual(self.invoke_fix(approved), 0)
        pending = self.save_fix_review(uncertainties=["Material fact not established"])
        self.assertEqual(self.invoke_fix(pending), 3)
        agy.assert_not_called()
        self.assertFalse((Path(self.target) / ".codex/codex-loop").exists())

    def test_modified_report_or_task_context_stops_before_execution(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        report = self.save_fix_review()
        report.write_text(self.native_report(findings=[self.finding(impact="Changed report")], overall_correctness="patch is incorrect"), encoding="utf-8")
        self.assertEqual(self.invoke_fix(report), 1)
        report = self.save_fix_review()
        (Path(self.target) / "docs/task.md").write_text("Changed acceptance.", encoding="utf-8")
        self.assertEqual(self.invoke_fix(report), 1)
        agy.assert_not_called()

    def test_changed_acceptance_does_not_reset_existing_cycle(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 0)
        (Path(self.target) / "docs/task.md").write_text("Changed acceptance.", encoding="utf-8")
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 3)
        self.assertEqual(agy.call_count, 1)

    def test_invalid_budget_config_or_counter_never_resets(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        report = self.save_fix_review()
        config = Path(self.target) / ".codex-loop.toml"
        for value in ("true", "0", '"2"', "[broken"):
            config.write_text(f"[collaboration]\nmax_fix_rounds = {value}\n", encoding="utf-8")
            self.assertEqual(self.invoke_fix(report), 1)
        config.unlink()
        self.assertEqual(self.invoke_fix(report), 0)
        state = next((Path(self.target) / ".codex/codex-loop").glob("fix-*.json"))
        state.write_text("{}", encoding="utf-8")
        self.assertEqual(self.invoke_fix(self.save_fix_review()), 1)
        self.assertEqual(agy.call_count, 1)

    def test_sidecar_output_cannot_overwrite_acceptance_or_previous_report(self):
        task = Path(self.target) / "review.txt.context.json"
        task.write_text("Acceptance document.", encoding="utf-8")
        self.assertEqual(self.invoke("--task", str(task), "--out", "review.txt"), 1)
        self.runner.assert_not_called()

    def test_approved_report_cannot_reconfirm_changed_acceptance(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        approved = self.save_fix_review(findings=[], overall_correctness="patch is correct")
        (Path(self.target) / "docs/task.md").write_text("New acceptance.", encoding="utf-8")
        self.assertEqual(self.invoke_fix(approved), 1)
        agy.assert_not_called()

    def test_uncertainty_report_is_saved_and_never_dispatched_for_repair(self):
        agy = self.enterContext(patch.object(codex_loop, "run_agy", return_value=True))
        pending = self.save_fix_review(findings=[], overall_correctness="patch is incorrect", uncertainties=["Missing runtime evidence"])
        self.assertEqual(self.invoke_fix(pending), 3)
        agy.assert_not_called()

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
