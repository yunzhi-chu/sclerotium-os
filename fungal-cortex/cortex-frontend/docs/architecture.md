# Fungal Cortex v2.0 — Architecture

> **Phase 5 | L6-Complete Agent Framework | QuantMind OS**

---

## 1. System Overview

Fungal Cortex v2.0 is an L6-complete bio-inspired agent framework that implements 18 mechanisms drawn from fungal biology, neuroscience, thermodynamics, and complex systems theory. The framework orchestrates 209 Skills across 14 modules through an 8-layer cognitive pipeline (L0--L7).

```
 ┌─────────────────────────────────────────────────────────────────┐
 │                     Fungal Cortex v2.0                           │
 │  ┌───────────────────────────────────────────────────────────┐  │
 │  │                    Web UI (Next.js 16)                     │  │
 │  │  Command Center │ Pipeline │ Agents │ Field │ L6 │ ...    │  │
 │  └──────────┬────────────────────────────────────────────────┘  │
 │             │                     │                              │
 │    ┌────────▼────────┐    ┌──────▼──────┐                       │
 │    │  REST API        │    │  WebSocket   │                       │
 │    │  (FastAPI)       │    │  (10Hz-1Hz)  │                       │
 │    └────────┬────────┘    └──────┬──────┘                       │
 │             │                     │                              │
 │    ┌────────▼────────────────────▼──────────────────────────┐   │
 │    │              L6 Cognitive Engine                        │   │
 │    │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ │   │
 │    │  │  M1  │ │  M2  │ │  M3  │ │  M4  │ │  M5  │ │  M6  │ │   │
 │    │  │ Meta │ │Ability│ │Cluster│ │ Goal │ │Security│ │ Rule │ │   │
 │    │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │   │
 │    │                    ┌────────┐                            │   │
 │    │                    │  M7    │                            │   │
 │    │                    │Emergence│                            │   │
 │    │                    └────────┘                            │   │
 │    └──────────────────────────────────────────────────────────┘   │
 │             │                                                     │
 │    ┌────────▼──────────────────────────────────────────────────┐  │
 │    │              Skill Registry (209 Skills)                   │  │
 │    │  Strategy │ Indicator │ Risk │ Research │ Trading │ ...   │  │
 │    └───────────────────────────────────────────────────────────┘  │
 │             │                                                     │
 │    ┌────────▼──────────────────────────────────────────────────┐  │
 │    │              Infrastructure Layer                          │  │
 │    │  Docker │ K8s │ ChromaDB │ Redis │ Prometheus │ Grafana   │  │
 │    └───────────────────────────────────────────────────────────┘  │
 └─────────────────────────────────────────────────────────────────┘
```

---

## 2. The 18 Bio-Inspired Mechanisms

| # | Mechanism | Bio-Inspiration | L6 Module | Purpose |
|---|-----------|----------------|-----------|---------|
| (i) | Stigmergy Field | Fungal colony signaling | M3 | PDE-based agent coordination |
| (ii) | Mycelial Morphogenesis | Hyphal network growth | M3 | Dynamic routing topology |
| (iii) | Dendritic Integration | Neural dendrite computation | M1 | Multi-signal aggregation |
| (iv) | Thermodynamic Engine | Boltzmann entropy | M1 | Free-energy minimization |
| (v) | Holographic Metacognition | Whole-brain encoding | M1 | Distributed self-model |
| (vi) | Quantum-Classical Dual-Mode | Quantum superposition | M1 | Parallel hypothesis testing |
| (vii) | Immune Layer | Adaptive immune system | M5 | Anomaly detection |
| (viii) | Autocatalytic Closure | Autopoiesis | M2 | Self-sustaining loops |
| (ix) | Morphogen Patterning | Developmental biology | M1 | Task differentiation |
| (x) | Synaptive Multilevel Evolution | Synaptic plasticity | M6 | Multi-scale optimization |
| (xi) | Enactive Inference | Active inference (Friston) | M4 | Perception-action coupling |
| (xii) | Panarchy Resilience | Ecological cycles | M3 | Adaptive reorganization |
| (xiii) | Architecture Auto-Refactor | Homeostasis | M1 | Self-modifying code |
| (xiv) | Sandbox Verification | Cellular compartmentalization | M2 | Isolated validation |
| (xv) | Global Goal Expander | Growth-driven tropism | M4 | Objective horizon expansion |
| (xvi) | Security Gateway | Cell membrane selectivity | M5 | Permission-controlled access |
| (xvii) | Dynamic Rule Evolution | Epigenetic regulation | M6 | Rule adaptation |
| (xviii) | Emergence Crystallizer | Pattern formation | M7 | Novelty capture |

---

## 3. L0--L7 Pipeline Architecture

The cognitive pipeline implements 8 processing layers, each building on the output of the previous.

```
  L0: DATA ──► Data ingestion, market feeds, WebSocket streams
                 │
  L1: ANALYSIS ──► Statistical indicators, pattern recognition, feature extraction
                 │
  L2: DEBATE ──► Multi-agent argumentation, dialectical synthesis
                 │
  L3: RESEARCH ──► Deep research, context gathering, information retrieval
                 │
  L4: TRADING ──► Signal generation, strategy execution, position management
                 │
  L5: RISK ──► Risk assessment, drawdown control, VaR computation
                 │
  L6: DECISION ──► Meta-cognitive arbitration, final decision, confidence scoring
                 │
  L7: META ──► Self-reflection, architecture evolution, knowledge distillation
```

**Key properties:**

- **Latency budget**: Each layer must complete within 100ms (L0--L4), 500ms (L5--L6), or 5s (L7).
- **Stigmergy coupling**: Every layer reads/writes to a shared PDE field (Stigmergy Field), enabling indirect agent coordination.
- **Observability**: Every layer emits structured telemetry at configurable sampling rates.
- **Graceful degradation**: If a layer times out, the pipeline uses the last known good output and flags a warning.

---

## 4. Frontend Architecture

### Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Framework | Next.js 16 (App Router) | SSR, routing, API routes |
| UI Library | React 19 | Component model |
| State | Zustand 5 | Client-side reactive state |
| 3D Visualization | React Three Fiber (R3F) | Mycelial network viz |
| Streaming | WebSocket (native) | Real-time data push |
| Styling | Tailwind CSS 4 + shadcn/ui | Design system |
| Workers | Web Workers (comlink) | Offload PDE solves |
| Build | Turbopack | Fast HMR |

### State Architecture (Zustand Stores)

```
  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
  │ pipelineStore │    │ fieldStore   │    │ agentStore   │
  │ - stages[]   │    │ - mesh       │    │ - agents[]   │
  │ - status     │    │ - params     │    │ - metrics    │
  │ - metrics    │    │ - heatmap    │    │ - topology   │
  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘
         │                   │                   │
  ┌──────▼───────────────────▼───────────────────▼───────┐
  │              WebSocket Manager (singleton)            │
  │  /ws/pipeline │ /ws/field │ /ws/agents │ /ws/l6     │
  └──────────────────────────────────────────────────────┘
         │                   │                   │
  ┌──────▼───────────────────▼───────────────────▼───────┐
  │              React Components (subscribers)           │
  │  PipelineGraph │ FieldCanvas │ AgentGrid │ L6Panel   │
  └──────────────────────────────────────────────────────┘
         │
  ┌──────▼───────────────────────────────────────────────┐
  │              Web Workers (PDE Solver)                 │
  │  stigmergy.worker.ts — Finite-difference PDE solve   │
  │  field.worker.ts — Mycelial growth simulation        │
  └──────────────────────────────────────────────────────┘
```

**Data flow principle**: WebSocket messages write directly to Zustand stores. React components subscribe to slices via selectors. Workers communicate via `postMessage` -- never block the main thread.

### Pages (10 total)

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | CommandCenter | System-wide dashboard, health, L6 status |
| `/pipeline` | PipelineView | L0--L7 pipeline visualization |
| `/agents` | AgentsView | Agent topology and metrics |
| `/field` | FieldView | 3D Stigmergy Field (R3F) |
| `/l6` | L6Panel | L6 module management |
| `/trading` | TradingView | Signals, positions, P&L |
| `/skills` | SkillsView | Skill browser, creator |
| `/audit` | AuditView | Full audit trail |
| `/market` | MarketView | Real-time market data |
| `/backtest` | BacktestView | Backtest runner, results |

---

## 5. Backend Architecture

```
  ┌─────────────────────────────────────────────────────────┐
  │                    FastAPI Server                         │
  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌─────────┐  │
  │  │ REST    │  │ WebSocket│  │ Event Bus│  │ LLM     │  │
  │  │ Router  │  │ Manager  │  │ (pub/sub)│  │ Router  │  │
  │  └────┬────┘  └────┬─────┘  └────┬─────┘  └────┬────┘  │
  │       │             │             │              │       │
  │  ┌────▼─────────────▼─────────────▼──────────────▼────┐  │
  │  │              L6 Engine Core                         │  │
  │  │  M1        M2        M3        M4        M5    M6  │  │
  │  └────────────────────────────────────────────────────┘  │
  │       │                                                  │
  │  ┌────▼──────────────────────────────────────────────┐   │
  │  │           Skill Registry (plugins)                  │   │
  │  │  StrategySkills │ IndicatorSkills │ RiskSkills     │   │
  │  └────────────────────────────────────────────────────┘   │
  └─────────────────────────────────────────────────────────┘
       │
  ┌────▼─────────────────────────────────────────────────────┐
  │                    Infrastructure                          │
  │  ChromaDB (vectors) │ Redis (cache) │ Celery (tasks)     │
  └──────────────────────────────────────────────────────────┘
```

### Event Bus

The event bus is a Redis-backed pub/sub system:

```
  bus.publish("pipeline:stage_complete", { stage: "L4", result })
  bus.subscribe("pipeline:stage_complete", handler)
```

Event types: `pipeline:*`, `agent:*`, `field:*`, `skill:*`, `l6:*`, `system:*`.

### Skill Registry

Skills are registered as Python dataclass plugins discovered at startup:

- 209 skills across 14 modules
- Each skill has a 6-dimensional DNA vector (see Skill Development Guide)
- Skills are hot-reloadable without server restart (file watcher)

### LLM Router

The LLM router selects the appropriate model per task:

| Task | Model | Fallback |
|------|-------|----------|
| Quick analysis | Claude Haiku 4.5 | -- |
| Strategy debate | Claude Sonnet 4.6 | GPT-4o |
| Deep research | Claude Opus 4.5 | Gemini Ultra |
| Code refactor | Claude Sonnet 4.6 | -- |

---

## 6. Data Flow: WebSocket to UI

```
  Backend                           Frontend
  ──────                           ───────

  FastAPI Producer                  Zustand Store
       │                                │
       │  ws.send({ type, data })        │
       ├───────────────────────────────► │  store.setState(data)
       │                                │
       │                                ├──► PipelineGraph (sub)
       │                                ├──► FieldCanvas (sub)
       │                                └──► L6Panel (sub)
       │
  [10Hz tick]    Web Worker (PDE)
                      │
                  field.worker.ts ◄── postMessage params
                      │
                  postMessage(result) ──► fieldStore
```

**Key properties:**
- WebSocket connections are long-lived; reconnection uses exponential backoff (1s, 2s, 4s, max 30s).
- Each message includes a sequence number for ordering and deduplication.
- The PDE worker runs at 20Hz and sends field snapshots at 5Hz to the main thread to avoid overwhelming the UI.

---

## 7. Deployment Architecture

```
  ┌─────────────────────────────────────────────────────┐
  │                  Kubernetes Cluster                   │
  │                                                      │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
  │  │ Frontend  │  │ Backend  │  │  L6 Engine Pod   │  │
  │  │ (Next.js) │  │(FastAPI) │  │  (stateful)      │  │
  │  │ replicas:3│  │replicas:3│  │  replicas:2      │  │
  │  └─────┬─────┘  └────┬─────┘  └────────┬─────────┘  │
  │        │              │                  │            │
  │  ┌─────▼──────────────▼──────────────────▼─────────┐ │
  │  │              Service Mesh (Istio)                │ │
  │  └─────────────────────────────────────────────────┘ │
  │        │              │                  │            │
  │  ┌─────▼──────┐ ┌────▼─────┐  ┌─────────▼────────┐ │
  │  │  ChromaDB  │ │  Redis   │  │  PostgreSQL       │ │
  │  │  (stateful)│ │ (HA)     │  │  (stateful)       │ │
  │  └────────────┘ └──────────┘  └──────────────────┘ │
  │                                                      │
  │  Prometheus ───► Grafana ───► Alertmanager           │
  └─────────────────────────────────────────────────────┘
```

### Components

| Component | Container | Replicas | Resource (req/limit) |
|-----------|-----------|----------|----------------------|
| Frontend | `cortex-frontend:latest` | 3 | 0.5/1 CPU, 512M/1G RAM |
| Backend | `cortex-backend:latest` | 3 | 1/2 CPU, 1G/2G RAM |
| L6 Engine | `cortex-l6:latest` | 2 | 2/4 CPU, 2G/4G RAM |
| ChromaDB | `chromadb/chroma:0.4.22` | 1 | 2/4 CPU, 4G/8G RAM |
| Redis | `redis:7-alpine` | 3 | 0.5/1 CPU, 256M/512M RAM |
| PostgreSQL | `postgres:16` | 1 | 1/2 CPU, 2G/4G RAM |

---

## 8. Security Architecture (M5 Security Gateway)

The M5 Security Gateway implements a cell-membrane-inspired permission model:

```
  Inbound Request
       │
  ┌────▼────┐
  │ HMAC    │── Invalid ──► 401
  │ Verify  │
  └────┬────┘
       │ Valid
  ┌────▼────┐
  │ Rate    │── Exceeded ──► 429
  │ Limiter │
  └────┬────┘
       │ OK
  ┌────▼────────┐
  │ Permission   │── Denied ──► 403
  │ Check (RBAC) │
  └────┬────────┘
       │ Granted
  ┌────▼────┐
  │  Audit  │
  │  Log    │
  └────┬────┘
       │
  ┌────▼────┐
  │ Execute │
  │ Request │
  └─────────┘
```

**Security layers:**
1. **HMAC signing** -- every API request includes `X-HMAC-Signature` header
2. **Rate limiting** -- 60 requests/min, 1000 requests/hour per API key
3. **RBAC** -- role-based access (admin, operator, analyst, viewer)
4. **Audit logging** -- all mutations logged to immutable audit store
5. **Immune Layer (vii)** -- anomaly detection on request patterns

---

## 9. Module Dependency Graph

```
  M1 (Metacognition)
   ├── M2 (Ability Creation)
   ├── M3 (Cluster Self-Organization)
   ├── M4 (Goal Expansion)
   ├── M5 (Security Gateway)
   ├── M6 (Rule Evolution)
   └── M7 (Emergence Capture)

  M2 ──► M4 (abilities inform goals)
  M3 ──► M1 (cluster state informs metacognition)
  M4 ──► M6 (goal changes trigger rule evolution)
  M5 ──► all (security wraps all modules)
  M6 ──► M2 (evolved rules create new abilities)
  M7 ──► M1 (captured patterns update self-model)
```

---

## 10. Monitoring & Observability

| Metric | Source | Instrumentation |
|--------|--------|-----------------|
| Pipeline latency per stage | Backend | Histogram (p50/p95/p99) |
| Agent count | L6 Engine | Gauge |
| Stigmergy field entropy | Field Server | Gauge |
| Skill invocations | Skill Registry | Counter |
| WebSocket message rate | WS Manager | Counter + Gauge |
| API error rate | REST Router | Counter (by status) |
| Memory/CPU | All containers | Container metrics |

All metrics are exposed at `/metrics` (Prometheus format) and visualized in Grafana dashboards.

---

## 11. Related Documents

- [API Reference](./api-reference.md) -- complete REST and WebSocket endpoint documentation
- [Skill Development Guide](./skill-development-guide.md) -- creating and publishing Skills
- [Operator Manual](./operator-manual.md) -- deployment, monitoring, troubleshooting
