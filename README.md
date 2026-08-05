# ckb-explorer-monitor

A lightweight **Prometheus exporter** that monitors the availability and core data health of the [CKB Explorer](https://github.com/nervosnetwork/ckb-explorer) API for **two environments: testnet and mainnet**.

---

## What it checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/statistics` | Overview stats: tip block number, 24h transactions, tx/min, average block time |
| `GET /api/v1/statistics/tip_block_number` | Tip block height |
| `GET /api/v1/blocks` | Latest blocks list availability, newest block number, and latest block timestamp |
| `GET /api/v1/transactions` | Latest transactions list availability, latest tx timestamp, block number, and status |
| `GET /api/v2/pending_transactions/count` | Number of pending transactions |
| CKB node JSON-RPC `get_tip_header` | Upstream CKB node tip block number (configured via `NODE_RPC_URL`) |
| Frontend `GET /` | Frontend reachability |

All v1 API calls include the required JSONAPI headers (`Content-Type: application/vnd.api+json`, `Accept: application/vnd.api+json`).

---

## Metrics exposed

| Metric | Labels | Description |
|--------|--------|-------------|
| `ckb_explorer_up` | `net`, `endpoint` | 1 if endpoint responded successfully, else 0 |
| `ckb_explorer_request_duration_seconds` | `net`, `endpoint` | Request latency |
| `ckb_explorer_http_status` | `net`, `endpoint` | Last HTTP status code |
| `ckb_explorer_tip_block_number` | `net` | Current tip block height |
| `ckb_explorer_transactions_last_24hrs` | `net` | Transactions in the last 24 hours |
| `ckb_explorer_transactions_count_per_minute` | `net` | Transactions per minute |
| `ckb_explorer_average_block_time` | `net` | Average block time (ms) |
| `ckb_explorer_latest_block_number` | `net` | Newest block number from `/blocks` |
| `ckb_explorer_latest_block_timestamp_seconds` | `net` | Newest block timestamp from `/blocks` (seconds) |
| `ckb_explorer_latest_block_age_seconds` | `net` | Age of newest block from `/blocks` (`now - latest_block_timestamp`) |
| `ckb_explorer_latest_transaction_timestamp_seconds` | `net` | Newest transaction timestamp from `/transactions` (seconds) |
| `ckb_explorer_latest_transaction_age_seconds` | `net` | Age of newest transaction from `/transactions` (`now - latest_transaction_timestamp`) |
| `ckb_explorer_latest_transaction_block_number` | `net` | Newest transaction block number from `/transactions` |
| `ckb_explorer_transaction_tip_lag_blocks` | `net` | Explorer tip lag to latest transaction block (`tip_block_number - latest_transaction_block_number`, min 0) |
| `ckb_explorer_latest_transaction_status` | `net`, `status` | Latest transaction status (`status` from `tx_status`, value is always 1) |
| `ckb_explorer_node_tip_block_number` | `net` | Upstream CKB node tip block number (from RPC `get_tip_header` on `NODE_RPC_URL`) |
| `ckb_explorer_sync_lag_blocks` | `net` | Blocks behind the upstream node tip (upstream_node_tip − explorer_indexed_tip, min 0) |
| `ckb_explorer_pending_transactions_count` | `net` | Number of pending transactions |
| `ckb_explorer_scrape_duration_seconds` | `net` | Total time for one full scrape cycle |
| `ckb_explorer_scrape_errors_total` | `net`, `endpoint` | Total scrape errors per endpoint (when check is down or raises exception) |

---

## Configuration

All configuration is via environment variables. Only **3 are required**:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | ✅ | — | Base URL of the CKB Explorer API (e.g. `https://mainnet-api.explorer.nervos.org`) |
| `NET` | ✅ | — | Network label: `mainnet` or `testnet` |
| `NODE_RPC_URL` | ✅ | — | URL of the upstream CKB JSON-RPC node used by this Explorer instance (e.g. `http://ckb-node:8114`). The exporter must be deployed in a network that can reach this node. |
| `EXPORTER_PORT` | — | `9333` | Port to expose `/metrics` on |
| `SCRAPE_INTERVAL` | — | `30` | Seconds between scrape cycles |
| `HTTP_TIMEOUT` | — | `10` | HTTP request timeout in seconds |

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

> **Note:** The example API URLs (`mainnet-api.explorer.nervos.org`, `testnet-api.explorer.nervos.org`) are defaults inferred from the CKB Explorer project. **Adjust them to the actual API domains used in your deployment.**

---

## Running with Docker

```bash
docker build -t ckb-explorer-monitor .

# Mainnet
docker run -d \
  -e API_URL=https://mainnet-api.explorer.nervos.org \
  -e NET=mainnet \
  -e NODE_RPC_URL=http://ckb-node:8114 \
  -p 9333:9333 \
  ckb-explorer-monitor

# Testnet
docker run -d \
  -e API_URL=https://testnet-api.explorer.nervos.org \
  -e NET=testnet \
  -e NODE_RPC_URL=http://ckb-testnet-node:8114 \
  -p 9334:9334 \
  -e EXPORTER_PORT=9334 \
  ckb-explorer-monitor
```

## Running with docker-compose

Both mainnet and testnet exporters start together. You must supply the upstream CKB node URLs via environment variables before starting:

```bash
export MAINNET_NODE_RPC_URL=http://ckb-mainnet-node:8114
export TESTNET_NODE_RPC_URL=http://ckb-testnet-node:8114
docker compose up -d
```

> **Note:** The exporter must be deployed in a network that can reach the upstream CKB node. Do not use public RPC endpoints — use the actual node that the Explorer instance connects to.

- Mainnet metrics: `http://localhost:9333/metrics`
- Testnet metrics: `http://localhost:9334/metrics`

---

## Prometheus scrape config

Add both jobs to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: ckb-explorer-mainnet
    static_configs:
      - targets: ['localhost:9333']

  - job_name: ckb-explorer-testnet
    static_configs:
      - targets: ['localhost:9334']
```

---

## Alerting rules

Pre-built Prometheus alerting rules are provided in [`prometheus/alerts.yml`](prometheus/alerts.yml).

### Loading the rules

Add a `rule_files` entry to your `prometheus.yml` **before** `scrape_configs`:

```yaml
rule_files:
  - /path/to/ckb-explorer-monitor/prometheus/alerts.yml

scrape_configs:
  - job_name: ckb-explorer-mainnet
    static_configs:
      - targets: ['localhost:9333']

  - job_name: ckb-explorer-testnet
    static_configs:
      - targets: ['localhost:9334']
```

### Alertmanager integration

To route alerts to a notification channel, add an `alerting` block and configure Alertmanager:

```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093   # replace with your Alertmanager host:port

rule_files:
  - /etc/prometheus/alerts.yml

scrape_configs:
  # ...
```

A minimal Alertmanager config skeleton (`alertmanager.yml`):

```yaml
route:
  receiver: 'default'
  group_by: ['alertname', 'net']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 4h

receivers:
  - name: 'default'
    # Add your notification channel here, e.g. slack_configs, webhook_configs, etc.
    # See https://prometheus.io/docs/alerting/latest/configuration/
```

### Default alert thresholds

| Alert | Severity | Condition | `for` |
|-------|----------|-----------|-------|
| `CKBExplorerEndpointDown` | critical | `ckb_explorer_up == 0` | 2 m |
| `CKBExplorerScapeTargetDown` | critical | `up{job=~"ckb-explorer-mainnet\|ckb-explorer-testnet"} == 0` | 2 m |
| `CKBExplorerSyncLagHigh` | warning | `ckb_explorer_sync_lag_blocks > 50` | 5 m |
| `CKBExplorerSyncLagCritical` | critical | `ckb_explorer_sync_lag_blocks > 200` | 5 m |
| `CKBExplorerLatestBlockStale` | warning | `ckb_explorer_latest_block_age_seconds > 300` | 5 m |
| `CKBExplorerLatestBlockStaleCritical` | critical | `ckb_explorer_latest_block_age_seconds > 900` | 5 m |
| `CKBExplorerLatestTransactionStale` | warning | `ckb_explorer_latest_transaction_age_seconds > 600` | 5 m |
| `CKBExplorerLatestTransactionStaleCritical` | critical | `ckb_explorer_latest_transaction_age_seconds > 1800` | 5 m |
| `CKBExplorerPendingTransactionsHigh` | warning | `ckb_explorer_pending_transactions_count > 5000` | 10 m |
| `CKBExplorerPendingTransactionsCritical` | critical | `ckb_explorer_pending_transactions_count > 20000` | 10 m |
| `CKBExplorerScrapeErrorsIncreasing` | warning | `rate(ckb_explorer_scrape_errors_total[5m]) > 0` | 5 m |

> **Tuning for production:** The thresholds above are conservative defaults. Adjust them to match your actual block time (~10 s on CKB mainnet), transaction throughput, and traffic patterns. For example, if you run a high-volume chain you may want to raise the pending-transaction thresholds; if you require tighter SLOs you may reduce the `for` durations.

### Validating rule syntax locally

```bash
promtool check rules prometheus/alerts.yml
```

### Using docker-compose with the optional Prometheus service

The `docker-compose.yml` ships an **optional** `prometheus` service (disabled by default via Docker Compose profiles) that mounts both the scrape config and the alerting rules:

```bash
# Start exporters + Prometheus
docker compose --profile prometheus up -d

# Exporters only (default behaviour — unchanged)
docker compose up -d
```

The Prometheus UI will be available at `http://localhost:9090`.

---

## Docker image

The image is automatically built and pushed to the **GitHub Container Registry** on every push to `main` and on new version tags (`v*`):

```
ghcr.io/jiangxianliang007/ckb-explorer-monitor:latest
```

To pull the latest image:

```bash
docker pull ghcr.io/jiangxianliang007/ckb-explorer-monitor:latest
```
---

## Grafana Dashboard

A pre-built Grafana dashboard is included at [`grafana/dashboards/ckb-explorer-monitor.json`](grafana/dashboards/ckb-explorer-monitor.json).

### Features

- **`net` variable** — top-of-dashboard dropdown that filters every panel to the selected network (`mainnet`, `testnet`, or any other value exposed by the exporter).
- **Environment URLs** — a Stat panel displays the **API URL** for the selected network.
- **Availability** — per-endpoint up/down status, plus availability history.
- **Block & Sync Status** — explorer tip, node tip, sync lag, and latest block age.
- **Transactions** — 24 h count, tx/min, pending count, latest transaction age.
- **Latency** — per-endpoint request duration, average block time, scrape duration.
- **Errors & HTTP Status** — scrape error rate and last HTTP status codes.

### 1. Configure the Prometheus datasource

In Grafana (**Configuration → Data Sources → Add data source → Prometheus**), set the URL to your Prometheus server (e.g. `http://localhost:9090`) and save.

### 2. Import the dashboard

1. In Grafana go to **Dashboards → Import**.
2. Click **Upload JSON file** and select `grafana/dashboards/ckb-explorer-monitor.json`.
3. Under **Prometheus** select the Prometheus datasource you configured above.
4. Click **Import**.

> **Tip:** You can also paste the JSON content directly into the *Import via panel JSON* text box.

### 3. Switch environment with `net`

At the top of the dashboard use the **Network** dropdown to switch between `mainnet`, `testnet`, or any other network label your exporter exposes.  
All panels update automatically.

### 4. Configure per-environment API URL

The dashboard displays the API URL from the `ckb_explorer_info` metric, which is set automatically by the exporter at startup using the `API_URL` environment variable.

No extra configuration is required — just ensure each exporter instance is started with the correct variable:

| Network | `API_URL` |
|---------|-----------|
| mainnet | `https://mainnet-api.explorer.nervos.org` |
| testnet | `https://testnet-api.explorer.nervos.org` |

### 5. Required Prometheus labels / metrics

The dashboard queries the following metrics (all exposed by this exporter):

| Metric | Labels | Used for |
|--------|--------|---------|
| `ckb_explorer_info` | `net`, `api_url` | Environment URL display |
| `ckb_explorer_up` | `net`, `endpoint` | Availability, `net` variable |
| `ckb_explorer_request_duration_seconds` | `net`, `endpoint` | Latency |
| `ckb_explorer_http_status` | `net`, `endpoint` | HTTP status table |
| `ckb_explorer_tip_block_number` | `net` | Explorer tip block |
| `ckb_explorer_node_tip_block_number` | `net` | Upstream CKB node tip block |
| `ckb_explorer_sync_lag_blocks` | `net` | Sync lag (upstream_node_tip − explorer_indexed_tip) |
| `ckb_explorer_latest_block_number` | `net` | Latest block from /blocks |
| `ckb_explorer_latest_block_age_seconds` | `net` | Block staleness |
| `ckb_explorer_transactions_last_24hrs` | `net` | 24 h transaction count |
| `ckb_explorer_transactions_count_per_minute` | `net` | Tx/min |
| `ckb_explorer_pending_transactions_count` | `net` | Pending transactions |
| `ckb_explorer_latest_transaction_age_seconds` | `net` | Transaction staleness |
| `ckb_explorer_average_block_time` | `net` | Average block time (ms) |
| `ckb_explorer_scrape_duration_seconds` | `net` | Exporter scrape cycle time |
| `ckb_explorer_scrape_errors_total` | `net`, `endpoint` | Error rate |

All metrics are emitted automatically by the exporter — no extra instrumentation is needed.
