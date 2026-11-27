"""Tests for bin/gatewayz-statusline. Standard library only, no network:
a local fake Gatewayz API stands in for api.gatewayz.ai.

    python3 -m unittest discover tests
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "bin", "gatewayz-statusline")
FIXTURES = os.path.join(ROOT, "tests", "fixtures")
KEY = "gw_test_not_a_real_key"


class FakeAPI(BaseHTTPRequestHandler):
    credits = 12.30
    usage_rows: list = []
    calls: list = []

    def do_GET(self):  # noqa: N802
        FakeAPI.calls.append(self.path)
        if self.headers.get("Authorization") != f"Bearer {KEY}":
            return self._send(401, {"detail": "Invalid API key"})
        url = urlparse(self.path)
        if url.path == "/user/balance":
            return self._send(200, {"credits": FakeAPI.credits, "status": "active"})
        if url.path == "/v1/usage":
            tag = parse_qs(url.query).get("tag", [None])[0]
            rows = [r for r in FakeAPI.usage_rows if r["tag"] == tag]
            return self._send(200, {"object": "list", "tag": tag, "data": rows, "measured": bool(rows)})
        self._send(404, {})

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


class StatuslineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), FakeAPI)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.transcript = os.path.join(self.tmp, "t.jsonl")
        shutil.copy(os.path.join(FIXTURES, "transcript.jsonl"), self.transcript)
        FakeAPI.credits, FakeAPI.usage_rows, FakeAPI.calls = 12.30, [], []

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_line(self, extra_env=None, session=None):
        if session is None:
            with open(os.path.join(FIXTURES, "session.json")) as f:
                session = json.load(f)
            session["transcript_path"] = self.transcript
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": self.tmp,
            "GATEWAYZ_STATUSLINE_DIR": os.path.join(self.tmp, "state"),
            "GATEWAYZ_STATUSLINE_CACHE_SECONDS": "0",
            "ANTHROPIC_BASE_URL": self.base,
            "ANTHROPIC_AUTH_TOKEN": KEY,
        }
        env.update(extra_env or {})
        out = subprocess.run([sys.executable, SCRIPT], input=json.dumps(session), env=env,
                             capture_output=True, text=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(out.stderr, "")
        return out.stdout.strip()

    def test_tokens_deduplicate_streamed_copies(self):
        line = self.run_line()
        # msg_1 counted once: sent = 1200+50000+2000 + 800 = 54000; out = 300+700
        self.assertIn("↑54.0k ↓1.0k tok", line)
        self.assertIn("moonshot/kimi-k2.6", line)

    def test_never_shows_claude_code_cost(self):
        self.assertNotIn("9.99", self.run_line())

    def test_estimated_spend_from_balance_delta(self):
        first = self.run_line()
        self.assertIn("~$0.00 this session", first)
        self.assertIn("$12.30 left", first)
        FakeAPI.credits = 11.87
        self.assertIn("~$0.43 this session · $11.87 left", self.run_line())

    def test_top_up_mid_session_resets_baseline(self):
        self.run_line()
        FakeAPI.credits = 50.0
        self.assertIn("~$0.00 this session · $50.00 left", self.run_line())

    def test_exact_spend_with_session_tag(self):
        FakeAPI.usage_rows = [{"tag": "cc-abc", "cost_usd": 0.4321, "calls": 3}]
        line = self.run_line({"ANTHROPIC_CUSTOM_HEADERS": "X-Gatewayz-Tag: cc-abc"})
        self.assertIn("$0.43 this session", line)
        self.assertNotIn("~", line)
        self.assertTrue(any(p.startswith("/v1/usage?tag=cc-abc") for p in FakeAPI.calls))

    def test_incremental_reads_pick_up_new_lines(self):
        self.run_line()
        with open(self.transcript, "a") as f:
            f.write(json.dumps({"type": "assistant", "message": {"id": "msg_3", "usage": {"input_tokens": 46000, "output_tokens": 9000}}}) + "\n")
        self.assertIn("↑100k ↓10.0k tok", self.run_line())

    def test_network_failure_drops_money_only(self):
        line = self.run_line({"ANTHROPIC_BASE_URL": "http://127.0.0.1:9"})
        self.assertEqual(line, "Gatewayz · moonshot/kimi-k2.6 · ↑54.0k ↓1.0k tok")

    def test_bad_key_drops_money_only(self):
        line = self.run_line({"ANTHROPIC_AUTH_TOKEN": "wrong"})
        self.assertNotIn("$", line)

    def test_key_never_printed_or_stored(self):
        line = self.run_line()
        self.assertNotIn(KEY, line)
        for folder, _, files in os.walk(self.tmp):
            for name in files:
                with open(os.path.join(folder, name), errors="ignore") as f:
                    self.assertNotIn(KEY, f.read(), name)

    def test_garbage_stdin(self):
        out = subprocess.run([sys.executable, SCRIPT], input="not json", capture_output=True, text=True,
                             env={"PATH": os.environ.get("PATH", ""), "HOME": self.tmp,
                                  "GATEWAYZ_STATUSLINE_DIR": os.path.join(self.tmp, "state")})
        self.assertEqual(out.stdout.strip(), "Gatewayz")

    def test_path_traversal_session_id_ignored(self):
        session = {"session_id": "../../evil", "transcript_path": self.transcript, "model": "m"}
        line = self.run_line(session=session)
        self.assertNotIn("tok", line)
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "evil.json")))


if __name__ == "__main__":
    unittest.main()
