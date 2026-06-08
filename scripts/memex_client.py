#!/usr/bin/env python3
"""
memex_client.py — minimal raw MCP streamable-HTTP client for Memex.

Shared by the daily *_tracker.py scripts so the project's headless writers all use
one battle-tested implementation. Has NO `claude` dependency — it speaks the MCP
protocol directly, so nothing here ever touches the Claude subscription quota.

    from memex_client import Memex
    mx = Memex("http://10.0.0.5:8765/mcp")
    mx.initialize()
    mx.write_note("Projects/Briefer/Status.md", body_markdown, {"tags": ["briefer"]})

write_note() is a rolling upsert: it updates the note if it exists, creates it if
not, then pushes the DB row out to the vault .md so a future re-bootstrap won't
clobber it.
"""
import json
import urllib.error
import urllib.request


class Memex:
    def __init__(self, url):
        self.url = url
        self.sid = None

    def _post(self, body):
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        if self.sid:
            req.add_header("Mcp-Session-Id", self.sid)
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            raw, sid = resp.read().decode("utf-8", "replace"), resp.headers.get("Mcp-Session-Id")
        except urllib.error.HTTPError as e:
            raw, sid = e.read().decode("utf-8", "replace"), e.headers.get("Mcp-Session-Id")
        if sid:
            self.sid = sid
        chunks = []
        for line in raw.splitlines():
            s = line.strip()
            if s.startswith("data:"):
                try:
                    chunks.append(json.loads(s[5:].strip()))
                except Exception:  # noqa: BLE001
                    pass
        if chunks:
            return chunks[-1]
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return {"raw": raw}

    def initialize(self):
        self._post({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "briefer-tracker", "version": "1.0"}}})
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call(self, name, args):
        return self._post({"jsonrpc": "2.0", "id": 9, "method": "tools/call",
                           "params": {"name": name, "arguments": args}})

    @staticmethod
    def _ok(resp):
        return isinstance(resp, dict) and "error" not in resp and not (resp.get("result", {}) or {}).get("isError")

    def read_note(self, path):
        return self.call("memex_read_note", {"path": path})

    def write_note(self, path, body, frontmatter):
        """Rolling upsert: update if exists, else create; then sync DB -> vault."""
        if not self._ok(self.call("memex_save_note", {"path": path, "body": body})):
            self.call("memex_create_note", {"path": path, "body": body, "frontmatter": frontmatter})
        self.call("memex_push_note", {"path": path})
