# ckb-explorer-monitor

A lightweight **Prometheus exporter** that monitors the availability and core data health of the [CKB Explorer](https://github.com/nervosnetwork/ckb-explorer) API for **two environments: testnet and mainnet**.

---

## What it checks

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/statistics` | Overview stats: tip block number, 24h transactions, tx/min, average block time |
| `GET /api/v1/statistics/tip_block_number` | Tip block height |
| `GET /api/v1/blocks` | Latest blocks list availability and newest block number |
| `GET /api/v1/transactions` | Latest transactions list availability |
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
| `ckb_explorer_latest_transactions_count` | `net` | Number of tx returned by `/transactions` |
| `ckb_explorer_frontend_up` | `net` | 1 if frontend is reachable, else 0 |
| `ckb_explorer_scrape_duration_seconds` | `net` | Total time for one full scrape cycle |

---

## Configuration

All configuration is via environment variables. Only **3 are required**:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_URL` | ✅ | — | Base URL of the CKB Explorer API (e.g. `https://mainnet-api.explorer.nervos.org`) |
| `FRONTEND_URL` | ✅ | — | Base URL of the CKB Explorer frontend (e.g. `https://explorer.nervos.org`) |
| `NET` | ✅ | — | Network label: `mainnet` or `testnet` |
| `EXPORTER_PORT` | — | `9333` | Port to expose `/metrics` on |
| `SCRAPE_INTERVAL` | — | `30` | Seconds between scrape cycles |
| `HTTP_TIMEOUT` | — | `10` | HTTP request timeout in seconds |

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

> **Note:** The example API URLs (`mainnet-api.explorer.nervos.org`, `testnet-api.explorer.nervos.org`) and frontend URLs (`explorer.nervos.org`, `pudge.explorer.nervos.org`) are defaults inferred from the CKB Explorer project. **Adjust them to the actual API domains used in your deployment.**

---

## Running with Docker

```bash
docker build -t ckb-explorer-monitor .

# Mainnet
docker run -d \
  -e API_URL=https://mainnet-api.explorer.nervos.org \
  -e FRONTEND_URL=https://explorer.nervos.org \
  -e NET=mainnet \
  -p 9333:9333 \
  ckb-explorer-monitor

# Testnet
docker run -d \
  -e API_URL=https://testnet-api.explorer.nervos.org \
  -e FRONTEND_URL=https://pudge.explorer.nervos.org \
  -e NET=testnet \
  -p 9334:9333 \
  ckb-explorer-monitor
```

## Running with docker-compose

Both mainnet and testnet exporters start together:

```bash
docker compose up -d
```

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

## Docker image

The image is automatically built and pushed to the **GitHub Container Registry** on every push to `main` and on new version tags (`v*`):

```
ghcr.io/jiangxianliang007/ckb-explorer-monitor:latest
```

To pull the latest image:

```bash
docker pull ghcr.io/jiangxianliang007/ckb-explorer-monitor:latest
```