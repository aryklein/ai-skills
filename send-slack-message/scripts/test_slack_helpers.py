"""Offline regression tests; no Slack messages are sent."""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError


def load_helper(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


post = load_helper("post-message")
resolve = load_helper("resolve-channel")
TOKEN = "test-only-selected-credential"
RECEIPT = {"ok": True, "channel": "C123", "ts": "123.456"}


def response(payload):
    return io.StringIO(json.dumps(payload))


class SlackHelpersTest(unittest.TestCase):
    def test_alternate_token_is_used_for_lookup_and_posting(self):
        env = {"SLACK_BOT_TOKEN": "wrong-default", "ALTERNATE_TOKEN": TOKEN}
        text = '✅ "quoted" \\ text\nActual newline\n'
        cases = [
            (resolve, ["#team", "--token-env", "ALTERNATE_TOKEN"],
             {"ok": True, "channels": [{"name": "team", "id": "C123"}]}),
            (post, ["C123", "--token-env", "ALTERNATE_TOKEN", "--thread-ts", "123.000"],
             RECEIPT),
        ]
        for module, args, result in cases:
            with self.subTest(helper=module.__name__):
                stdout, stderr = io.StringIO(), io.StringIO()
                argv = [module.__name__, *args]
                with patch.dict("os.environ", env, clear=True), \
                     patch("sys.argv", argv), patch("sys.stdin", io.StringIO(text)), \
                     patch.object(module, "urlopen", return_value=response(result)) as send, \
                     contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    self.assertEqual(module.main(), 0)
                request = send.call_args.args[0]
                self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
                self.assertNotIn(TOKEN, " ".join(argv))
                self.assertNotIn(TOKEN, stdout.getvalue() + stderr.getvalue())
                if module is post:
                    self.assertEqual(json.loads(request.data), {
                        "channel": "C123", "text": text, "thread_ts": "123.000",
                    })
                    self.assertEqual(json.loads(stdout.getvalue()), RECEIPT)
                    self.assertEqual(request.get_method(), "POST")

    def test_default_token_and_unthreaded_message(self):
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": TOKEN}, clear=True), \
             patch("sys.argv", ["post-message", "C123"]), \
             patch("sys.stdin", io.StringIO("hello")), \
             patch.object(post, "urlopen", return_value=response(RECEIPT)) as send, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(post.main(), 0)
        request = send.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)
        self.assertNotIn("thread_ts", json.loads(request.data))

    def test_missing_alternate_token_does_not_fall_back(self):
        for module in (post, resolve):
            with self.subTest(helper=module.__name__), \
                 patch.dict("os.environ", {"SLACK_BOT_TOKEN": TOKEN}, clear=True), \
                 patch("sys.argv", [module.__name__, "C123", "--token-env", "MISSING"]), \
                 patch.object(module, "urlopen") as send, \
                 contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(module.main(), 1)
                send.assert_not_called()

    def test_empty_message_is_rejected_before_network(self):
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": TOKEN}, clear=True), \
             patch("sys.argv", ["post-message", "C123"]), \
             patch("sys.stdin", io.StringIO(" \n")), \
             patch.object(post, "urlopen") as send, \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(post.main(), 1)
            send.assert_not_called()

    def test_api_errors_and_invalid_receipts_are_rejected(self):
        for result in (
            {"ok": False, "error": "missing_scope", "needed": "chat:write"},
            {"ok": True}, ["invalid"], {"ok": "true", "channel": "C123", "ts": "123"},
        ):
            with self.subTest(result=result), \
                 patch.object(post, "urlopen", return_value=response(result)) as send:
                with self.assertRaises(RuntimeError):
                    post.post_message(TOKEN, "C123", "hello")
                send.assert_called_once()

    def test_uncertain_delivery_is_not_retried(self):
        for error in (URLError("failed"), TimeoutError(),
                      HTTPError("https://slack.com", 429, "limited", {}, None)):
            with self.subTest(error=type(error).__name__), \
                 patch.object(post, "urlopen", side_effect=error) as send:
                with self.assertRaisesRegex(RuntimeError, "before retrying"):
                    post.post_message(TOKEN, "C123", "hello")
                send.assert_called_once()
        with patch.object(post, "urlopen", return_value=io.StringIO("not json")) as send:
            with self.assertRaisesRegex(RuntimeError, "before retrying"):
                post.post_message(TOKEN, "C123", "hello")
            send.assert_called_once()

    def test_rate_limit_reports_retry_window_without_retrying(self):
        for header, expected in (
            ("30", "Wait at least 30 seconds"),
            ("0", "Wait at least 0 seconds"),
            (None, "retry window is unknown"),
            ("invalid", "retry window is unknown"),
            ("-1", "retry window is unknown"),
        ):
            with self.subTest(header=header):
                headers = {} if header is None else {"Retry-After": header}
                body = io.BytesIO(b"rate limited")
                error = HTTPError("https://slack.com", 429, "limited", headers, body)
                with patch.object(post, "urlopen", side_effect=error) as send:
                    with self.assertRaisesRegex(RuntimeError, expected):
                        post.post_message(TOKEN, "C123", "hello")
                    send.assert_called_once()
                self.assertTrue(body.closed)

    def test_api_error_redacts_token_and_returns_failure(self):
        stderr = io.StringIO()
        with patch.dict("os.environ", {"SLACK_BOT_TOKEN": TOKEN}, clear=True), \
             patch("sys.argv", ["post-message", "C123"]), \
             patch("sys.stdin", io.StringIO("hello")), \
             patch.object(post, "urlopen", return_value=response({"ok": False, "error": TOKEN})), \
             contextlib.redirect_stderr(stderr):
            self.assertEqual(post.main(), 1)
        self.assertNotIn(TOKEN, stderr.getvalue())
        self.assertIn("[REDACTED]", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
