"""Load and validate configuration from environment variables."""

import os
import sys


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: required environment variable '{name}' is not set.", file=sys.stderr)
        sys.exit(1)
    return value


class Config:
    api_url: str
    net: str
    node_rpc_url: str
    exporter_port: int
    scrape_interval: int
    http_timeout: int

    def __init__(self) -> None:
        self.api_url = _require("API_URL").rstrip("/")
        self.net = _require("NET")
        self.node_rpc_url = _require("NODE_RPC_URL").rstrip("/")

        try:
            self.exporter_port = int(os.environ.get("EXPORTER_PORT", "9333"))
        except ValueError:
            print("ERROR: EXPORTER_PORT must be an integer.", file=sys.stderr)
            sys.exit(1)

        try:
            self.scrape_interval = int(os.environ.get("SCRAPE_INTERVAL", "30"))
        except ValueError:
            print("ERROR: SCRAPE_INTERVAL must be an integer.", file=sys.stderr)
            sys.exit(1)

        try:
            self.http_timeout = int(os.environ.get("HTTP_TIMEOUT", "10"))
        except ValueError:
            print("ERROR: HTTP_TIMEOUT must be an integer.", file=sys.stderr)
            sys.exit(1)
