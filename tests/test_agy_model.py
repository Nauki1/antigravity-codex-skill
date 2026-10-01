"""Regression coverage for the model passed to the implementation provider."""

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


class TestAntigravityModel(unittest.TestCase):
    def test_initial_implementation_and_custom_prompt_select_flash_high(self):
        with tempfile.TemporaryDirectory(prefix="codex_agy_model_") as target:
            with patch.object(codex_loop.subprocess, "run") as runner:
                runner.return_value = subprocess.CompletedProcess([], 0, json.dumps({"status": "SUCCESS", "response": "Done"}), "")
                for arguments in ([], ["--prompt", "Implement the agreed task"]):
                    with self.subTest(arguments=arguments):
                        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                            with self.assertRaises(SystemExit) as caught:
                                codex_loop.main(["exec-agy", "--project", target, *arguments])
                        self.assertEqual(caught.exception.code, 0)
                        command = runner.call_args.args[0]
                        self.assertEqual(command.count("--model"), 1)
                        self.assertEqual(command[command.index("--model") + 1], "gemini-3.8-flash-high")
                        self.assertEqual(runner.call_args.kwargs["cwd"], str(Path(target).resolve()))


if __name__ == "__main__":
    unittest.main()
