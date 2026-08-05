"""Probe functions for each monitored CKB Explorer endpoint."""

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, Optional

import requests

log = logging.getLogger(__name__)

_MAX_LOG_RESPONSE_LENGTH = 512

if TYPE_CHECKING:
    from app.config import Config

JSONAPI_HEADERS = {
    "Content-Type": "application/vnd.api+json",
    "Accept": "application/vnd.api+json",
}

# Hardcoded CKB node RPC endpoints, keyed by NET value.
_NODE_RPC_URLS: Dict[str, str] = {
    "testnet": "https://testnet.ckbapp.dev",
    "mainnet": "https://mainnet.ckbapp.dev",
}


@dataclass
class CheckResult:
    endpoint: str
    up: bool
    status_code: int
    duration: float
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert a value (often a string from JSONAPI) to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_timestamp_seconds(value: Any) -> Optional[float]:
    """Parse timestamp that may be seconds or milliseconds into seconds."""
    ts = _safe_float(value)
    if ts is None:
        return None
    if ts > 1e12:
        ts = ts / 1000.0
    return ts


def check_statistics(api_url: str, timeout: int) -> CheckResult:
    """GET /api/v1/statistics — overview stats."""
    url = f"{api_url}/api/v1/statistics"
    start = time.monotonic()
    try:
        resp = requests.get(url, headers=JSONAPI_HEADERS, timeout=timeout)
        duration = time.monotonic() - start
        status_code = resp.status_code

        if status_code != 200:
            return CheckResult(
                endpoint="statistics",
                up=False,
                status_code=status_code,
                duration=duration,
                error=f"HTTP {status_code}",
            )

        body = resp.json()
        attrs = body.get("data", {}).get("attributes", {})

        tip_block_number = _safe_float(attrs.get("tip_block_number"))
        if tip_block_number is None:
            return CheckResult(
                endpoint="statistics",
                up=False,
                status_code=status_code,
                duration=duration,
                error="tip_block_number missing or invalid",
            )

        return CheckResult(
            endpoint="statistics",
            up=True,
            status_code=status_code,
            duration=duration,
            data={
                "tip_block_number": tip_block_number,
                "transactions_last_24hrs": _safe_float(attrs.get("transactions_last_24hrs")),
                "transactions_count_per_minute": _safe_float(
                    attrs.get("transactions_count_per_minute")
                ),
                "average_block_time": _safe_float(attrs.get("average_block_time")),
            },
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="statistics",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )


def check_tip_block_number(api_url: str, timeout: int) -> CheckResult:
    """GET /api/v1/statistics/tip_block_number — tip block height."""
    url = f"{api_url}/api/v1/statistics/tip_block_number"
    start = time.monotonic()
    try:
        resp = requests.get(url, headers=JSONAPI_HEADERS, timeout=timeout)
        duration = time.monotonic() - start
        status_code = resp.status_code

        if status_code != 200:
            return CheckResult(
                endpoint="tip_block_number",
                up=False,
                status_code=status_code,
                duration=duration,
                error=f"HTTP {status_code}",
            )

        body = resp.json()
        attrs = body.get("data", {}).get("attributes", {})
        tip = _safe_float(attrs.get("tip_block_number"))

        if tip is None:
            return CheckResult(
                endpoint="tip_block_number",
                up=False,
                status_code=status_code,
                duration=duration,
                error="tip_block_number missing or invalid",
            )

        return CheckResult(
            endpoint="tip_block_number",
            up=True,
            status_code=status_code,
            duration=duration,
            data={"tip_block_number": tip},
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="tip_block_number",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )


def check_blocks(api_url: str, timeout: int) -> CheckResult:
    """GET /api/v1/blocks — latest blocks list availability."""
    url = f"{api_url}/api/v1/blocks"
    start = time.monotonic()
    try:
        resp = requests.get(url, headers=JSONAPI_HEADERS, timeout=timeout)
        duration = time.monotonic() - start
        status_code = resp.status_code

        if status_code != 200:
            return CheckResult(
                endpoint="blocks",
                up=False,
                status_code=status_code,
                duration=duration,
                error=f"HTTP {status_code}",
            )

        body = resp.json()
        data_list = body.get("data", [])

        if not isinstance(data_list, list) or len(data_list) == 0:
            return CheckResult(
                endpoint="blocks",
                up=False,
                status_code=status_code,
                duration=duration,
                error="blocks data list is empty or invalid",
            )

        attrs = data_list[0].get("attributes", {})
        latest_number = _safe_float(attrs.get("number"))
        latest_timestamp_seconds = _parse_timestamp_seconds(attrs.get("timestamp"))

        return CheckResult(
            endpoint="blocks",
            up=True,
            status_code=status_code,
            duration=duration,
            data={
                "latest_block_number": latest_number,
                "latest_block_timestamp_seconds": latest_timestamp_seconds,
            },
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="blocks",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )


def check_transactions(api_url: str, timeout: int) -> CheckResult:
    """GET /api/v1/transactions — latest transactions list availability."""
    url = f"{api_url}/api/v1/transactions"
    start = time.monotonic()
    try:
        resp = requests.get(url, headers=JSONAPI_HEADERS, timeout=timeout)
        duration = time.monotonic() - start
        status_code = resp.status_code

        if status_code != 200:
            return CheckResult(
                endpoint="transactions",
                up=False,
                status_code=status_code,
                duration=duration,
                error=f"HTTP {status_code}",
            )

        body = resp.json()
        data_list = body.get("data", [])

        if not isinstance(data_list, list) or len(data_list) == 0:
            return CheckResult(
                endpoint="transactions",
                up=False,
                status_code=status_code,
                duration=duration,
                error="transactions data list is empty or invalid",
            )

        attrs = data_list[0].get("attributes", {})
        tx_status = attrs.get("tx_status")
        if tx_status is None and attrs.get("is_cellbase") is not None:
            tx_status = "committed"

        return CheckResult(
            endpoint="transactions",
            up=True,
            status_code=status_code,
            duration=duration,
            data={
                "latest_transaction_timestamp_seconds": _parse_timestamp_seconds(
                    attrs.get("block_timestamp")
                ),
                "latest_transaction_block_number": _safe_float(attrs.get("block_number")),
                "latest_transaction_status": str(tx_status) if tx_status is not None else None,
            },
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="transactions",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )


def check_node_tip(cfg: "Config") -> CheckResult:
    """JSON-RPC get_tip_header — fetch the CKB node tip block number."""
    rpc_url = _NODE_RPC_URLS.get(cfg.net)
    if rpc_url is None:
        return CheckResult(
            endpoint="node_tip",
            up=False,
            status_code=0,
            duration=0.0,
            error=f"unknown net '{cfg.net}': no RPC URL configured",
        )
    payload = {"id": 1, "jsonrpc": "2.0", "method": "get_tip_header", "params": []}
    start = time.monotonic()
    try:
        resp = requests.post(rpc_url, json=payload, timeout=cfg.http_timeout)
        duration = time.monotonic() - start
        status_code = resp.status_code
        if status_code != 200:
            return CheckResult(
                endpoint="node_tip",
                up=False,
                status_code=status_code,
                duration=duration,
                error=f"HTTP {status_code}",
            )
        body = resp.json()
        number_hex = body.get("result", {}).get("number")
        if number_hex is None:
            return CheckResult(
                endpoint="node_tip",
                up=False,
                status_code=status_code,
                duration=duration,
                error="number missing from get_tip_header result",
            )
        node_tip = int(number_hex, 16)
        return CheckResult(
            endpoint="node_tip",
            up=True,
            status_code=status_code,
            duration=duration,
            data={"node_tip_block_number": float(node_tip)},
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="node_tip",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )


def _parse_pending_count(body: Any) -> Optional[float]:
    """Extract the pending transaction count from various API response shapes.

    Accepted shapes (all treat 0 as a valid count):
      - Raw numeric JSON: ``42`` or ``0``
      - ``{"data": 0}`` / ``{"data": 42}`` — data field is the count
      - ``{"data": {"count": 42}}``
      - ``{"data": {"attributes": {"count": "42"}}}`` — JSONAPI envelope
      - ``{"count": 42}``
    """
    # Raw numeric response (the entire body is a number).
    if isinstance(body, (int, float)):
        return float(body)

    if not isinstance(body, dict):
        return None

    data = body.get("data")

    # {"data": 0} or {"data": 42} — the value itself is the count.
    if isinstance(data, (int, float)):
        return float(data)

    if isinstance(data, dict):
        # {"data": {"attributes": {"count": ...}}} — JSONAPI envelope.
        count = data.get("attributes", {}).get("count")
        if count is None:
            # {"data": {"count": ...}}
            count = data.get("count")
        if count is not None:
            return _safe_float(count)

    # {"count": ...} — flat top-level key.
    if "count" in body:
        return _safe_float(body["count"])

    return None


def check_pending_transactions(cfg: "Config") -> CheckResult:
    """GET /api/v2/pending_transactions/count — pending transaction count."""
    url = f"{cfg.api_url}/api/v2/pending_transactions/count"
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=cfg.http_timeout)
        duration = time.monotonic() - start
        status_code = resp.status_code
        if status_code != 200:
            return CheckResult(
                endpoint="pending_transactions",
                up=False,
                status_code=status_code,
                duration=duration,
                error=f"HTTP {status_code}",
            )
        try:
            body = resp.json()
        except Exception:
            body = None
        count = _parse_pending_count(body)
        if count is None:
            snippet = resp.text[:_MAX_LOG_RESPONSE_LENGTH]
            log.warning(
                "pending_transactions: could not parse count from response: %s", snippet
            )
            return CheckResult(
                endpoint="pending_transactions",
                up=False,
                status_code=status_code,
                duration=duration,
                error="count missing from pending_transactions response",
            )
        return CheckResult(
            endpoint="pending_transactions",
            up=True,
            status_code=status_code,
            duration=duration,
            data={"pending_transactions_count": count},
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="pending_transactions",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )
