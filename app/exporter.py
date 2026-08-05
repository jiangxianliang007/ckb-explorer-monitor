"""Prometheus exporter: metric definitions, scrape loop, and HTTP server."""

import logging
import threading
import time
from typing import Optional

from prometheus_client import Counter, Gauge, Info, start_http_server

from app.checks import (
    check_blocks,
    check_node_tip,
    check_pending_transactions,
    check_statistics,
    check_tip_block_number,
    check_transactions,
)
from app.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Metric definitions
# ---------------------------------------------------------------------------

_LABEL_NET_ENDPOINT = ["net", "endpoint"]
_LABEL_NET = ["net"]

i_info = Info(
    "ckb_explorer",
    "Static information about the monitored CKB Explorer environment",
    _LABEL_NET,
)

g_up = Gauge(
    "ckb_explorer_up",
    "1 if endpoint responded successfully, else 0",
    _LABEL_NET_ENDPOINT,
)
g_duration = Gauge(
    "ckb_explorer_request_duration_seconds",
    "Request latency in seconds",
    _LABEL_NET_ENDPOINT,
)
g_status = Gauge(
    "ckb_explorer_http_status",
    "Last HTTP status code",
    _LABEL_NET_ENDPOINT,
)
g_tip_block_number = Gauge(
    "ckb_explorer_tip_block_number",
    "Current tip block height",
    _LABEL_NET,
)
g_transactions_last_24hrs = Gauge(
    "ckb_explorer_transactions_last_24hrs",
    "Transactions in the last 24 hours",
    _LABEL_NET,
)
g_transactions_per_minute = Gauge(
    "ckb_explorer_transactions_count_per_minute",
    "Transactions per minute",
    _LABEL_NET,
)
g_average_block_time = Gauge(
    "ckb_explorer_average_block_time",
    "Average block time in milliseconds",
    _LABEL_NET,
)
g_latest_block_number = Gauge(
    "ckb_explorer_latest_block_number",
    "Newest block number from /blocks",
    _LABEL_NET,
)
g_latest_block_timestamp_seconds = Gauge(
    "ckb_explorer_latest_block_timestamp_seconds",
    "Newest block timestamp from /blocks in seconds",
    _LABEL_NET,
)
g_latest_block_age_seconds = Gauge(
    "ckb_explorer_latest_block_age_seconds",
    "Age of newest block from /blocks in seconds",
    _LABEL_NET,
)
g_latest_transaction_timestamp_seconds = Gauge(
    "ckb_explorer_latest_transaction_timestamp_seconds",
    "Newest transaction block timestamp from /transactions in seconds",
    _LABEL_NET,
)
g_latest_transaction_age_seconds = Gauge(
    "ckb_explorer_latest_transaction_age_seconds",
    "Age of newest transaction from /transactions in seconds",
    _LABEL_NET,
)
g_latest_transaction_block_number = Gauge(
    "ckb_explorer_latest_transaction_block_number",
    "Newest transaction block number from /transactions",
    _LABEL_NET,
)
g_transaction_tip_lag_blocks = Gauge(
    "ckb_explorer_transaction_tip_lag_blocks",
    "Difference between explorer tip and latest transaction block (min 0)",
    _LABEL_NET,
)
g_latest_transaction_status = Gauge(
    "ckb_explorer_latest_transaction_status",
    "Latest transaction status from /transactions (value is always 1)",
    ["net", "status"],
)
g_node_tip_block_number = Gauge(
    "ckb_explorer_node_tip_block_number",
    "CKB node tip block number (from RPC get_tip_header)",
    _LABEL_NET,
)
g_sync_lag_blocks = Gauge(
    "ckb_explorer_sync_lag_blocks",
    "Difference between node tip and explorer tip (node_tip - explorer_tip, min 0)",
    _LABEL_NET,
)
g_pending_transactions_count = Gauge(
    "ckb_explorer_pending_transactions_count",
    "Number of pending transactions reported by the explorer",
    _LABEL_NET,
)
g_scrape_duration = Gauge(
    "ckb_explorer_scrape_duration_seconds",
    "Total time taken for one full scrape cycle",
    _LABEL_NET,
)
g_scrape_errors_total = Counter(
    "ckb_explorer_scrape_errors_total",
    "Total scrape errors per endpoint",
    _LABEL_NET_ENDPOINT,
)

_last_latest_transaction_status = {}


# ---------------------------------------------------------------------------
# Scrape loop
# ---------------------------------------------------------------------------


def _scrape(cfg: Config) -> None:
    net = cfg.net
    scrape_start = time.monotonic()
    now = time.time()

    explorer_tip: Optional[float] = None

    def _inc_scrape_error(endpoint: str) -> None:
        g_scrape_errors_total.labels(net=net, endpoint=endpoint).inc()

    # --- /api/v1/statistics ---
    try:
        r = check_statistics(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if not r.up:
            _inc_scrape_error(r.endpoint)
        if r.up:
            d = r.data
            if d.get("tip_block_number") is not None:
                explorer_tip = d["tip_block_number"]
                g_tip_block_number.labels(net=net).set(d["tip_block_number"])
            if d.get("transactions_last_24hrs") is not None:
                g_transactions_last_24hrs.labels(net=net).set(d["transactions_last_24hrs"])
            if d.get("transactions_count_per_minute") is not None:
                g_transactions_per_minute.labels(net=net).set(d["transactions_count_per_minute"])
            if d.get("average_block_time") is not None:
                g_average_block_time.labels(net=net).set(d["average_block_time"])
        if r.error:
            log.warning("statistics check failed: %s", r.error)
    except Exception:
        _inc_scrape_error("statistics")
        log.exception("unexpected error in check_statistics")

    # --- /api/v1/statistics/tip_block_number ---
    try:
        r = check_tip_block_number(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if not r.up:
            _inc_scrape_error(r.endpoint)
        if r.error:
            log.warning("tip_block_number check failed: %s", r.error)
    except Exception:
        _inc_scrape_error("tip_block_number")
        log.exception("unexpected error in check_tip_block_number")

    # --- /api/v1/blocks ---
    try:
        r = check_blocks(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if not r.up:
            _inc_scrape_error(r.endpoint)
        if r.up:
            latest_block_number = r.data.get("latest_block_number")
            latest_block_timestamp_seconds = r.data.get("latest_block_timestamp_seconds")
            if latest_block_number is not None:
                g_latest_block_number.labels(net=net).set(latest_block_number)
            if latest_block_timestamp_seconds is not None:
                g_latest_block_timestamp_seconds.labels(net=net).set(latest_block_timestamp_seconds)
                g_latest_block_age_seconds.labels(net=net).set(
                    max(now - latest_block_timestamp_seconds, 0)
                )
            else:
                log.warning("blocks check missing latest block timestamp")
        if r.error:
            log.warning("blocks check failed: %s", r.error)
    except Exception:
        _inc_scrape_error("blocks")
        log.exception("unexpected error in check_blocks")

    # --- /api/v1/transactions ---
    try:
        r = check_transactions(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if not r.up:
            _inc_scrape_error(r.endpoint)
        if r.up:
            latest_transaction_timestamp_seconds = r.data.get("latest_transaction_timestamp_seconds")
            latest_transaction_block_number = r.data.get("latest_transaction_block_number")
            latest_transaction_status = r.data.get("latest_transaction_status")
            if latest_transaction_timestamp_seconds is not None:
                g_latest_transaction_timestamp_seconds.labels(net=net).set(
                    latest_transaction_timestamp_seconds
                )
                g_latest_transaction_age_seconds.labels(net=net).set(
                    max(now - latest_transaction_timestamp_seconds, 0)
                )
            else:
                log.warning("transactions check missing latest transaction timestamp")
            if latest_transaction_block_number is not None:
                g_latest_transaction_block_number.labels(net=net).set(
                    latest_transaction_block_number
                )
                if explorer_tip is not None:
                    g_transaction_tip_lag_blocks.labels(net=net).set(
                        max(explorer_tip - latest_transaction_block_number, 0)
                    )
            else:
                log.warning("transactions check missing latest transaction block number")
            if latest_transaction_status:
                previous_status = _last_latest_transaction_status.get(net)
                if previous_status and previous_status != latest_transaction_status:
                    g_latest_transaction_status.labels(net=net, status=previous_status).set(0)
                g_latest_transaction_status.labels(
                    net=net, status=latest_transaction_status
                ).set(1)
                _last_latest_transaction_status[net] = latest_transaction_status
            else:
                log.warning("transactions check missing latest transaction status")
        if r.error:
            log.warning("transactions check failed: %s", r.error)
    except Exception:
        _inc_scrape_error("transactions")
        log.exception("unexpected error in check_transactions")

    # --- CKB node tip (RPC get_tip_header) ---
    node_tip: Optional[float] = None
    try:
        r = check_node_tip(cfg)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if not r.up:
            _inc_scrape_error(r.endpoint)
        if r.up and r.data.get("node_tip_block_number") is not None:
            node_tip = r.data["node_tip_block_number"]
            g_node_tip_block_number.labels(net=net).set(node_tip)
        if r.error:
            log.warning("node_tip check failed: %s", r.error)
    except Exception:
        _inc_scrape_error("node_tip")
        log.exception("unexpected error in check_node_tip")

    # --- sync lag (node tip vs explorer tip) ---
    if node_tip is not None and explorer_tip is not None:
        g_sync_lag_blocks.labels(net=net).set(max(node_tip - explorer_tip, 0))

    # --- pending transactions count ---
    try:
        r = check_pending_transactions(cfg)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if not r.up:
            _inc_scrape_error(r.endpoint)
        if r.up and r.data.get("pending_transactions_count") is not None:
            g_pending_transactions_count.labels(net=net).set(r.data["pending_transactions_count"])
        if r.error:
            log.warning("pending_transactions check failed: %s", r.error)
    except Exception:
        _inc_scrape_error("pending_transactions")
        log.exception("unexpected error in check_pending_transactions")

    g_scrape_duration.labels(net=net).set(time.monotonic() - scrape_start)


def _loop(cfg: Config) -> None:
    log.info(
        "Starting scrape loop: net=%s api=%s interval=%ds",
        cfg.net,
        cfg.api_url,
        cfg.scrape_interval,
    )
    while True:
        try:
            _scrape(cfg)
        except Exception:
            log.exception("scrape cycle failed unexpectedly")
        time.sleep(cfg.scrape_interval)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    cfg = Config()
    log.info("Starting CKB Explorer exporter on port %d (net=%s)", cfg.exporter_port, cfg.net)

    # Publish static environment info so Grafana dashboards can display the
    # API URL for each net without hard-coding it.
    i_info.labels(net=cfg.net).info(
        {
            "api_url": cfg.api_url,
        }
    )

    start_http_server(cfg.exporter_port)

    t = threading.Thread(target=_loop, args=(cfg,), daemon=True)
    t.start()
    t.join()


if __name__ == "__main__":
    main()
