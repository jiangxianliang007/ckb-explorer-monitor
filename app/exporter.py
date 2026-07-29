"""Prometheus exporter: metric definitions, scrape loop, and HTTP server."""

import logging
import threading
import time
from typing import Optional

from prometheus_client import Gauge, start_http_server

from app.checks import (
    check_blocks,
    check_frontend,
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
g_latest_tx_count = Gauge(
    "ckb_explorer_latest_transactions_count",
    "Number of transactions returned by /transactions",
    _LABEL_NET,
)
g_frontend_up = Gauge(
    "ckb_explorer_frontend_up",
    "1 if frontend is reachable, else 0",
    _LABEL_NET,
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


# ---------------------------------------------------------------------------
# Scrape loop
# ---------------------------------------------------------------------------


def _scrape(cfg: Config) -> None:
    net = cfg.net
    scrape_start = time.monotonic()

    explorer_tip: Optional[float] = None

    # --- /api/v1/statistics ---
    try:
        r = check_statistics(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
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
        log.exception("unexpected error in check_statistics")

    # --- /api/v1/statistics/tip_block_number ---
    try:
        r = check_tip_block_number(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if r.error:
            log.warning("tip_block_number check failed: %s", r.error)
    except Exception:
        log.exception("unexpected error in check_tip_block_number")

    # --- /api/v1/blocks ---
    try:
        r = check_blocks(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if r.up and r.data.get("latest_block_number") is not None:
            g_latest_block_number.labels(net=net).set(r.data["latest_block_number"])
        if r.error:
            log.warning("blocks check failed: %s", r.error)
    except Exception:
        log.exception("unexpected error in check_blocks")

    # --- /api/v1/transactions ---
    try:
        r = check_transactions(cfg.api_url, cfg.http_timeout)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if r.up and r.data.get("latest_transactions_count") is not None:
            g_latest_tx_count.labels(net=net).set(r.data["latest_transactions_count"])
        if r.error:
            log.warning("transactions check failed: %s", r.error)
    except Exception:
        log.exception("unexpected error in check_transactions")

    # --- frontend ---
    try:
        r = check_frontend(cfg.frontend_url, cfg.http_timeout)
        g_frontend_up.labels(net=net).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if r.error:
            log.warning("frontend check failed: %s", r.error)
    except Exception:
        log.exception("unexpected error in check_frontend")

    # --- CKB node tip (RPC get_tip_header) ---
    node_tip: Optional[float] = None
    try:
        r = check_node_tip(cfg)
        g_up.labels(net=net, endpoint=r.endpoint).set(1 if r.up else 0)
        g_duration.labels(net=net, endpoint=r.endpoint).set(r.duration)
        g_status.labels(net=net, endpoint=r.endpoint).set(r.status_code)
        if r.up and r.data.get("node_tip_block_number") is not None:
            node_tip = r.data["node_tip_block_number"]
            g_node_tip_block_number.labels(net=net).set(node_tip)
        if r.error:
            log.warning("node_tip check failed: %s", r.error)
    except Exception:
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
        if r.up and r.data.get("pending_transactions_count") is not None:
            g_pending_transactions_count.labels(net=net).set(r.data["pending_transactions_count"])
        if r.error:
            log.warning("pending_transactions check failed: %s", r.error)
    except Exception:
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
    start_http_server(cfg.exporter_port)

    t = threading.Thread(target=_loop, args=(cfg,), daemon=True)
    t.start()
    t.join()


if __name__ == "__main__":
    main()
