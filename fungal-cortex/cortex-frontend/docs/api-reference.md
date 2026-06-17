# Fungal Cortex v2.0 -- API Reference

> **REST + WebSocket | HMAC Authentication | Rate Limited**

Base URL: `https://api.cortex.quantmind.ai/v1`

---

## 1. Authentication

All REST API requests require HMAC-SHA256 signing.

### Request Signing

```
Header: X-HMAC-Signature: <base64(hmac-sha256(api_secret, string_to_sign))>
Header: X-HMAC-Key: <api_key_id>
Header: X-HMAC-Timestamp: <unix_timestamp_ms>
```

**String to sign** (concatenated):

```
{HTTP_METHOD}\n{URI_PATH}\n{X-HMAC-Timestamp}\n{REQUEST_BODY}
```

**Example (Node.js):**

```typescript
import { createHmac } from "crypto";

function signRequest(
  method: string,
  path: string,
  body: string,
  secret: string,
  timestamp: number,
): string {
  const strToSign = `${method}\n${path}\n${timestamp}\n${body}`;
  return createHmac("sha256", secret).update(strToSign).digest("base64");
}
```

**Example (Python):**

```python
import hmac, hashlib, base64

def sign_request(method: str, path: str, body: str, secret: str, timestamp: int) -> str:
    str_to_sign = f"{method}\n{path}\n{timestamp}\n{body}"
    sig = hmac.new(secret.encode(), str_to_sign.encode(), hashlib.sha256)
    return base64.b64encode(sig.digest()).decode()
```

### Rate Limits

| Window | Limit | Headers |
|--------|-------|---------|
| Per minute | 60 | `X-RateLimit-Remaining`, `X-RateLimit-Reset` |
| Per hour | 1000 | `X-RateLimit-Hourly-Remaining` |

When exceeded, the API returns `429 Too Many Requests` with a `Retry-After` header.

---

## 2. REST Endpoints

### 2.1 System Health

```
GET /api/health
```

**Response `200 OK`:**

```json
{
  "status": "ok",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "modules": {
    "l6_engine": "healthy",
    "skill_registry": "healthy",
    "stigmergy_field": "healthy",
    "chromadb": "healthy",
    "redis": "healthy"
  },
  "pipeline_status": {
    "current_layer": "L4",
    "throughput_hz": 9.8,
    "avg_latency_ms": 42.3
  },
  "agent_count": 47,
  "active_skills": 209
}
```

**Response `503 Service Unavailable`** (if any critical module is down):

```json
{
  "status": "degraded",
  "version": "2.0.0",
  "modules": {
    "chromadb": "unreachable"
  },
  "message": "ChromaDB connection failed"
}
```

---

### 2.2 Skills

```
GET /api/skills
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | -- | Search query (filters by name, description) |
| `module` | string | -- | Filter by module (`strategy`, `indicator`, `risk`, etc.) |
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page (max 100) |
| `sort` | enum | `name` | Sort field: `name`, `created`, `version` |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "strat-ma-crossover",
      "name": "MA Crossover Strategy",
      "description": "Moving average crossover with dynamic thresholds",
      "module": "strategy",
      "version": "2.1.0",
      "dna": [0.85, 0.42, 0.13, 0.67, 0.91, 0.34],
      "status": "active",
      "created": "2025-11-15T10:30:00Z",
      "updated": "2026-06-10T08:12:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 209,
    "total_pages": 11
  }
}
```

---

```
GET /api/skills/:id
```

**Response `200 OK`:**

```json
{
  "id": "strat-ma-crossover",
  "name": "MA Crossover Strategy",
  "description": "Moving average crossover with dynamic thresholds",
  "module": "strategy",
  "version": "2.1.0",
  "dna": [0.85, 0.42, 0.13, 0.67, 0.91, 0.34],
  "status": "active",
  "source": "python",
  "dependencies": ["indicator-sma", "indicator-ema"],
  "parameters": {
    "fast_period": { "type": "int", "default": 10, "min": 2, "max": 100 },
    "slow_period": { "type": "int", "default": 30, "min": 5, "max": 500 },
    "threshold": { "type": "float", "default": 0.02, "min": 0.001, "max": 1.0 }
  },
  "metrics": {
    "invocations": 1247,
    "avg_latency_ms": 12.3,
    "success_rate": 0.998
  },
  "created": "2025-11-15T10:30:00Z",
  "updated": "2026-06-10T08:12:00Z"
}
```

**Response `404 Not Found`:**

```json
{
  "error": "skill_not_found",
  "message": "Skill 'strat-unknown' not found",
  "request_id": "req_abc123"
}
```

---

### 2.3 Strategies

```
GET /api/strategies
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `q` | string | -- | Search query |
| `asset_class` | enum | -- | `equity`, `crypto`, `fx`, `commodity` |
| `risk_level` | enum | -- | `low`, `medium`, `high` |
| `page` | int | 1 | Page number |
| `limit` | int | 20 | Items per page |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "strat-ma-crossover",
      "name": "MA Crossover Strategy",
      "asset_class": "equity",
      "risk_level": "medium",
      "win_rate": 0.62,
      "sharpe_ratio": 1.8,
      "max_drawdown": 0.12,
      "status": "active"
    }
  ],
  "pagination": { "page": 1, "limit": 20, "total": 45, "total_pages": 3 }
}
```

---

### 2.4 Backtest

```
POST /api/backtest
```

**Request Body:**

```json
{
  "strategy_id": "strat-ma-crossover",
  "symbols": ["BTC/USD", "ETH/USD"],
  "timeframe": "1h",
  "start": "2025-01-01T00:00:00Z",
  "end": "2026-06-01T00:00:00Z",
  "initial_capital": 100000.0,
  "commission": 0.001,
  "parameters": {
    "fast_period": 10,
    "slow_period": 30,
    "threshold": 0.02
  }
}
```

**Response `202 Accepted`:**

```json
{
  "backtest_id": "bt_7f8a3b2c",
  "status": "queued",
  "estimated_completion_s": 45
}
```

**Poll for results:**

```
GET /api/backtest/:id
```

**Response `200 OK` (completed):**

```json
{
  "backtest_id": "bt_7f8a3b2c",
  "status": "completed",
  "strategy_id": "strat-ma-crossover",
  "results": {
    "total_return": 0.234,
    "annualized_return": 0.187,
    "sharpe_ratio": 1.82,
    "sortino_ratio": 2.15,
    "max_drawdown": 0.12,
    "win_rate": 0.62,
    "total_trades": 847,
    "avg_hold_time_h": 24.3,
    "equity_curve": [100000, 100500, 101200, ...],
    "trades": [
      {
        "timestamp": "2025-01-15T10:30:00Z",
        "symbol": "BTC/USD",
        "side": "buy",
        "entry_price": 42000.0,
        "exit_price": 43500.0,
        "pnl": 1500.0,
        "pnl_pct": 0.0357
      }
    ]
  },
  "completed_at": "2026-06-12T14:35:00Z"
}
```

---

### 2.5 Audit Trail

```
GET /api/audit
```

**Query Parameters:**

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `from` | ISO8601 | 24h ago | Start time |
| `to` | ISO8601 | now | End time |
| `action` | string | -- | Filter by action type |
| `actor` | string | -- | Filter by actor (user or agent ID) |
| `page` | int | 1 | Page number |
| `limit` | int | 50 | Items per page |

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "aud_001",
      "timestamp": "2026-06-12T14:30:00Z",
      "actor": "user_admin",
      "action": "skill.deploy",
      "target": "strat-ma-crossover",
      "details": { "version": "2.1.0" },
      "ip": "10.0.1.50",
      "hmac_key_id": "key_admin_01"
    }
  ],
  "pagination": { "page": 1, "limit": 50, "total": 3402 }
}
```

---

### 2.6 L6 Module Endpoints

```
POST /api/l6/scan
```

Triggers a full M1 (Metacognition) scan of the system.

**Response `202 Accepted`:**

```json
{
  "scan_id": "scan_4f2a",
  "status": "started",
  "message": "M1 full scan initiated"
}
```

---

```
POST /api/l6/refactor/:id/approve
```

Approves an auto-refactor recommendation (mechanism xiii).

**Request Body:**

```json
{
  "approved": true,
  "comment": "Approved -- improves pipeline latency by factor 2"
}
```

**Response `200 OK`:**

```json
{
  "refactor_id": "ref_7b3c",
  "status": "approved",
  "applied": true,
  "result": "pipeline latency reduced from 84ms to 41ms"
}
```

---

```
POST /api/l6/create-ability
```

Creates a new ability via M2 (Ability Creation).

**Request Body:**

```json
{
  "name": "Sentiment Aggregator",
  "description": "Aggregates sentiment from 5 sources with weighted voting",
  "dna": [0.7, 0.3, 0.9, 0.5, 0.2, 0.8],
  "module": "analysis",
  "parameters": {
    "sources": ["twitter", "news", "onchain", "fear_greed", "volume"],
    "weights": { "twitter": 0.2, "news": 0.3, "onchain": 0.25, "fear_greed": 0.1, "volume": 0.15 }
  }
}
```

**Response `201 Created`:**

```json
{
  "ability_id": "ab_sentiment_agg_v1",
  "status": "created",
  "sandbox_status": "pending"
}
```

---

### 2.7 Goal Management

```
GET /api/goals
```

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "goal_001",
      "description": "Reduce max drawdown below 8%",
      "status": "active",
      "progress": 0.65,
      "created": "2026-05-01T00:00:00Z",
      "target_date": "2026-07-01T00:00:00Z",
      "exploration_score": 0.42
    }
  ]
}
```

---

### 2.8 Security Gateway

```
GET /api/gateway/services
```

**Response `200 OK`:**

```json
{
  "data": [
    {
      "service": "skill-registry",
      "status": "healthy",
      "requests_last_hour": 12400,
      "blocked_requests": 3,
      "rate_limit_hits": 12,
      "avg_latency_ms": 8.5
    }
  ]
}
```

---

### 2.9 Rule Evolution

```
GET /api/rules/tests
```

**Response `200 OK`:**

```json
{
  "data": [
    {
      "id": "ab_001",
      "rule": "max_position_size",
      "variant_a": "0.05",
      "variant_b": "0.08",
      "status": "running",
      "samples": 342,
      "winner": null,
      "started": "2026-06-10T00:00:00Z"
    }
  ]
}
```

---

## 3. WebSocket Endpoints

### Connection

```
ws://api.cortex.quantmind.ai/v1/ws/{channel}
```

Authentication is via the first message sent (not the URL):

```json
{
  "type": "auth",
  "hmac_key": "key_admin_01",
  "hmac_signature": "base64signature",
  "timestamp": 1718200000000
}
```

### Channels

| Channel | Frequency | Payload Size | Purpose |
|---------|-----------|--------------|---------|
| `/ws/health` | 1 Hz | ~200 bytes | System health status |
| `/ws/pipeline` | 10 Hz | ~1 KB | L0--L7 pipeline stage outputs |
| `/ws/agents` | 5 Hz | ~2 KB | Agent states, metrics, topology |
| `/ws/field` | 20 Hz | ~4 KB | Stigmergy field grid snapshots |
| `/ws/l6` | 1 Hz | ~3 KB | L6 module events |
| `/ws/trading` | 10 Hz | ~1 KB | Signals, orders, positions |
| `/ws/market` | realtime | ~500 bytes | Market tick data |

### Message Format

All WebSocket messages follow a uniform envelope:

```typescript
interface WSMessage<T = unknown> {
  type: string;        // Message type identifier
  channel: string;     // Originating channel
  seq: number;         // Monotonic sequence number (per channel)
  ts: number;          // Unix timestamp (milliseconds)
  data: T;             // Payload
  meta?: {
    latency_ms?: number;
    source?: string;
  };
}
```

### Channel-Specific Messages

**`/ws/health` (1 Hz):**

```json
{
  "type": "health.update",
  "channel": "health",
  "seq": 4512,
  "ts": 1718200001000,
  "data": {
    "status": "ok",
    "cpu_pct": 34.2,
    "memory_mb": 1240,
    "pipeline_hz": 9.8,
    "agent_count": 47,
    "uptime_h": 72.3
  }
}
```

**`/ws/pipeline` (10 Hz):**

```json
{
  "type": "pipeline.stage",
  "channel": "pipeline",
  "seq": 89234,
  "ts": 1718200000100,
  "data": {
    "layer": "L4",
    "status": "complete",
    "latency_ms": 42.3,
    "stage_input": { "signals": ["buy_btc"] },
    "stage_output": { "confidence": 0.87 }
  }
}
```

**`/ws/field` (20 Hz):**

```json
{
  "type": "field.snapshot",
  "channel": "field",
  "seq": 178400,
  "ts": 1718200000050,
  "data": {
    "grid": { "width": 64, "height": 64 },
    "values": [0.12, 0.34, 0.56, ...],
    "entropy": 0.78,
    "gradient_magnitude": 0.23
  }
}
```

**`/ws/l6` (1 Hz):**

```json
{
  "type": "l6.event",
  "channel": "l6",
  "seq": 3601,
  "ts": 1718200001000,
  "data": {
    "module": "M1",
    "event": "metacognitive_scan",
    "summary": "Scanned 47 agents, 0 anomalies detected",
    "details": { "agents_scanned": 47, "anomalies": 0 }
  }
}
```

**`/ws/trading` (10 Hz):**

```json
{
  "type": "trading.signal",
  "channel": "trading",
  "seq": 45200,
  "ts": 1718200000100,
  "data": {
    "symbol": "BTC/USD",
    "action": "buy",
    "confidence": 0.82,
    "price": 67200.50,
    "quantity": 1.5,
    "strategy_id": "strat-ma-crossover"
  }
}
```

---

## 4. Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `auth_invalid_signature` | 401 | HMAC signature does not match |
| `auth_expired_timestamp` | 401 | Timestamp differs by more than 300s |
| `auth_invalid_key` | 401 | API key not found or revoked |
| `rate_limit_exceeded` | 429 | Request rate exceeds limit |
| `rate_limit_hourly` | 429 | Hourly quota exhausted |
| `skill_not_found` | 404 | Skill ID does not exist |
| `strategy_not_found` | 404 | Strategy ID does not exist |
| `backtest_not_found` | 404 | Backtest ID not found |
| `validation_error` | 422 | Request body failed validation |
| `refactor_not_found` | 404 | Refactor recommendation not found |
| `refactor_already_processed` | 409 | Refactor already approved/rejected |
| `l6_busy` | 503 | L6 engine is processing another operation |
| `sandbox_timeout` | 504 | Sandbox verification timed out |
| `internal_error` | 500 | Unexpected server error |

### Error Response Envelope

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. 58 requests in the last 60 seconds.",
  "request_id": "req_xyz789",
  "details": {
    "limit": 60,
    "window_s": 60,
    "retry_after_s": 12
  }
}
```

---

## 5. TypeScript Types

```typescript
// === Auth ===
interface HMACHeaders {
  "X-HMAC-Signature": string;
  "X-HMAC-Key": string;
  "X-HMAC-Timestamp": number;
}

// === Pagination ===
interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

interface PaginatedResponse<T> {
  data: T[];
  pagination: Pagination;
}

// === Health ===
interface HealthResponse {
  status: "ok" | "degraded";
  version: string;
  uptime_seconds: number;
  modules: Record<string, string>;
  pipeline_status: {
    current_layer: string;
    throughput_hz: number;
    avg_latency_ms: number;
  };
  agent_count: number;
  active_skills: number;
}

// === Skills ===
interface Skill {
  id: string;
  name: string;
  description: string;
  module: string;
  version: string;
  dna: [number, number, number, number, number, number];
  status: "active" | "inactive" | "sandbox";
  created: string;
  updated: string;
}

interface SkillDetail extends Skill {
  source: string;
  dependencies: string[];
  parameters: Record<string, ParameterDef>;
  metrics: {
    invocations: number;
    avg_latency_ms: number;
    success_rate: number;
  };
}

interface ParameterDef {
  type: "int" | "float" | "string" | "bool";
  default: unknown;
  min?: number;
  max?: number;
}

// === Backtest ===
interface BacktestRequest {
  strategy_id: string;
  symbols: string[];
  timeframe: string;
  start: string;
  end: string;
  initial_capital: number;
  commission: number;
  parameters: Record<string, unknown>;
}

interface BacktestResult {
  backtest_id: string;
  status: "queued" | "running" | "completed" | "failed";
  results?: {
    total_return: number;
    annualized_return: number;
    sharpe_ratio: number;
    sortino_ratio: number;
    max_drawdown: number;
    win_rate: number;
    total_trades: number;
    equity_curve: number[];
    trades: Trade[];
  };
}

interface Trade {
  timestamp: string;
  symbol: string;
  side: "buy" | "sell";
  entry_price: number;
  exit_price: number;
  pnl: number;
  pnl_pct: number;
}

// === WebSocket ===
interface WSMessage<T = unknown> {
  type: string;
  channel: string;
  seq: number;
  ts: number;
  data: T;
  meta?: {
    latency_ms?: number;
    source?: string;
  };
}

// === Error ===
interface APIError {
  error: string;
  message: string;
  request_id: string;
  details?: Record<string, unknown>;
}
```

---

## 6. API Versioning

The API is versioned via the URL path (`/v1/`). The current version is v1. When breaking changes are introduced, a new version path (`/v2/`) will be released with a minimum 6-month deprecation window for the previous version.

---

## 7. Related Documents

- [Architecture Overview](./architecture.md) -- system design, pipeline, mechanisms
- [Skill Development Guide](./skill-development-guide.md) -- creating and publishing Skills
- [Operator Manual](./operator-manual.md) -- deployment, monitoring, troubleshooting
