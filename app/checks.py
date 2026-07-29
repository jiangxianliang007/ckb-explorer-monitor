"""Probe functions for each monitored CKB Explorer endpoint."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import requests

JSONAPI_HEADERS = {
    "Content-Type": "application/vnd.api+json",
    "Accept": "application/vnd.api+json",
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

        latest_number = _safe_float(data_list[0].get("attributes", {}).get("number"))

        return CheckResult(
            endpoint="blocks",
            up=True,
            status_code=status_code,
            duration=duration,
            data={"latest_block_number": latest_number},
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

        return CheckResult(
            endpoint="transactions",
            up=True,
            status_code=status_code,
            duration=duration,
            data={"latest_transactions_count": float(len(data_list))},
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


def check_frontend(frontend_url: str, timeout: int) -> CheckResult:
    """GET / — frontend reachability check."""
    url = frontend_url
    start = time.monotonic()
    try:
        resp = requests.get(url, timeout=timeout, allow_redirects=True)
        duration = time.monotonic() - start
        status_code = resp.status_code
        up = status_code < 400
        return CheckResult(
            endpoint="frontend",
            up=up,
            status_code=status_code,
            duration=duration,
            error=None if up else f"HTTP {status_code}",
        )
    except Exception as exc:
        duration = time.monotonic() - start
        return CheckResult(
            endpoint="frontend",
            up=False,
            status_code=0,
            duration=duration,
            error=str(exc),
        )
