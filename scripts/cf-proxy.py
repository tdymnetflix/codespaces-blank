#!/usr/bin/env python3
"""Local Cloudflare AI proxy that rotates accounts on HTTP 429 responses."""

import http.client
import http.server
import json
import os
import random
import re
import socket
import sys
import time
import urllib.error
import urllib.request
from base64 import b64encode


CREDENTIALS_URL = os.environ.get(
    "CF_CREDENTIALS_URL",
    "https://bitbucket.org/hermes-new/hermes/raw/main/credentials/cloudflare.txt",
)
LISTEN_HOST = os.environ.get("CF_PROXY_HOST", "127.0.0.1")
LISTEN_PORT = int(os.environ.get("CF_PROXY_PORT", "8788"))
MAX_RETRIES = int(os.environ.get("CF_MAX_RETRIES", "20"))
CREDENTIALS_TIMEOUT = int(os.environ.get("CF_CREDENTIALS_TIMEOUT", "15"))
ACCOUNT_TTL = 15


def load_accounts():
    """Fetch and parse blank-line-separated Cloudflare credential blocks."""
    request = urllib.request.Request(
        CREDENTIALS_URL,
        headers={"User-Agent": "hermes-cf-proxy/1.0"},
    )

    username = os.environ.get("BITBUCKET_USERNAME")
    app_password = os.environ.get("BITBUCKET_APP_PASSWORD")
    if username and app_password:
        credentials = b64encode(f"{username}:{app_password}".encode()).decode()
        request.add_header("Authorization", f"Basic {credentials}")

    try:
        with urllib.request.urlopen(request, timeout=CREDENTIALS_TIMEOUT) as response:
            text = response.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, UnicodeDecodeError) as error:
        raise RuntimeError(f"Unable to load Cloudflare credentials from {CREDENTIALS_URL}: {error}") from error

    accounts = []
    for block in re.split(r"\n\s*\n", text.strip()):
        account = {}
        for line in block.splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                key, value = line.split("=", 1)
                account[key.strip()] = value.strip()
        if account.get("ACCOUNT_ID") and account.get("API_KEY"):
            accounts.append(account)

    if not accounts:
        raise RuntimeError(f"No Cloudflare credentials found at {CREDENTIALS_URL}")
    return accounts


ACCOUNTS = load_accounts()
print(f"Loaded {len(ACCOUNTS)} Cloudflare accounts", file=sys.stderr)

CURRENT_ACCOUNT = None
LAST_ACCOUNT_TIMESTAMP = 0


def pick_account(force=False):
    global CURRENT_ACCOUNT, LAST_ACCOUNT_TIMESTAMP
    now = time.time()
    if force or CURRENT_ACCOUNT is None or now - LAST_ACCOUNT_TIMESTAMP >= ACCOUNT_TTL:
        CURRENT_ACCOUNT = random.choice(ACCOUNTS)
        LAST_ACCOUNT_TIMESTAMP = now
    return CURRENT_ACCOUNT


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format_string, *args):
        print(f"{self.client_address[0]} - {format_string % args}", file=sys.stderr)

    def send_body(self, status, body, headers=None):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self.send_body(200, json.dumps({"ok": True, "accounts": len(ACCOUNTS)}))
            return
        self.send_body(404, b"")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length else b""
        forwarded_headers = {
            key: self.headers[key]
            for key in ("Content-Type", "Accept")
            if key in self.headers
        }

        tried_keys = set()
        last_status = 429
        last_body = b""
        max_attempts = min(len(ACCOUNTS), MAX_RETRIES)

        while len(tried_keys) < max_attempts:
            account = pick_account(force=bool(tried_keys))
            api_key = account["API_KEY"]
            if api_key in tried_keys:
                continue
            tried_keys.add(api_key)

            upstream_path = self.path.removeprefix("/v1")
            path = f"/client/v4/accounts/{account['ACCOUNT_ID']}/ai/v1{upstream_path}"
            headers = {**forwarded_headers, "Authorization": f"Bearer {api_key}"}
            connection = http.client.HTTPSConnection("api.cloudflare.com", timeout=60)
            try:
                connection.request("POST", path, body=body, headers=headers)
                response = connection.getresponse()
                response_body = response.read()
                if response.status != 429:
                    output_headers = {
                        key: value
                        for key, value in response.getheaders()
                        if key.lower() not in {"transfer-encoding", "connection", "content-encoding"}
                    }
                    self.send_body(response.status, response_body, output_headers)
                    return
                last_status = response.status
                last_body = response_body
                time.sleep(0.2)
            finally:
                connection.close()

        self.send_body(last_status, last_body, {"Content-Type": "application/json"})


def find_free_port(host, start=8788):
    port = start
    while True:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex((host, port)) != 0:
                return port
        port += 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--find-port":
        print(find_free_port(LISTEN_HOST, LISTEN_PORT))
        raise SystemExit(0)

    server = http.server.HTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"Listening on http://{LISTEN_HOST}:{LISTEN_PORT}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down", file=sys.stderr)