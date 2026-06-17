# Fungal Cortex v2.0 -- Operator Manual

> **Deployment, monitoring, maintenance, and incident response**

---

## 1. Prerequisites

| Component | Version | Purpose |
|-----------|---------|---------|
| Docker | 24+ | Container runtime |
| Docker Compose | 2.24+ | Local orchestration |
| Kubernetes | 1.28+ | Production orchestration |
| Python | 3.12 | Backend runtime |
| Node.js | 22 | Frontend build/runtime |
| Helm | 3.14+ | K8s package manager |
| kubectl | 1.28+ | K8s CLI |
| PostgreSQL | 16 | Relational data |
| Redis | 7 | Cache, pub/sub, rate limiting |
| ChromaDB | 0.4.22 | Vector embeddings |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_DSN` | Y | -- | PostgreSQL connection string |
| `REDIS_URL` | Y | `redis://localhost:6379` | Redis connection |
| `CHROMA_HOST` | Y | `localhost` | ChromaDB host |
| `CHROMA_PORT` | N | `8000` | ChromaDB port |
| `HMAC_SECRET_KEY` | Y | -- | API signing secret |
| `LLM_API_KEY` | Y | -- | LLM provider key |
| `LLM_MODEL` | N | `claude-sonnet-4-6` | Default model |
| `LOG_LEVEL` | N | `INFO` | Logging level |
| `METRICS_ENABLED` | N | `true` | Prometheus metrics |
| `RATE_LIMIT_PER_MIN` | N | `60` | API rate limit |
| `FIELD_GRID_SIZE` | N | `64` | Stigmergy field grid |
| `MAX_AGENTS` | N | `100` | Max concurrent agents |

---

## 2. Quick Start (Docker Compose)

```bash
# 1. Clone the repository
git clone https://github.com/quantmind/cortex.git
cd cortex

# 2. Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and secrets

# 3. Start all services
docker compose up -d

# 4. Verify all services are healthy
docker compose ps

# 5. Check the health endpoint
curl http://localhost:8000/api/health

# 6. Access the frontend
open http://localhost:3000
```

### Docker Compose Services

```yaml
services:
  frontend:      # Next.js on :3000
  backend:       # FastAPI on :8000
  l6-engine:     # L6 core engine
  chromadb:      # Vector store on :8001
  redis:         # Cache/pubsub on :6379
  postgres:      # Database on :5432
  prometheus:    # Metrics on :9090
  grafana:       # Dashboards on :3001
```

### Useful Docker Commands

```bash
# View logs for all services
docker compose logs -f

# View logs for a specific service
docker compose logs -f backend

# Restart a service
docker compose restart l6-engine

# Rebuild and restart
docker compose up -d --build backend

# Scale a service
docker compose up -d --scale backend=3

# Stop everything
docker compose down

# Stop and remove volumes (warning: deletes data)
docker compose down -v
```

---

## 3. Production Kubernetes Deployment

### Step 1: Prepare the cluster

```bash
# Create namespace
kubectl create namespace cortex

# Add required secrets
kubectl create secret generic cortex-secrets \
  --namespace=cortex \
  --from-literal=hmac-secret-key="$(openssl rand -base64 32)" \
  --from-literal=llm-api-key="your-llm-key" \
  --from-literal=postgres-dsn="postgresql://user:pass@postgres:5432/cortex"

# Add Helm repos
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
```

### Step 2: Deploy infrastructure

```bash
# PostgreSQL
helm install postgres bitnami/postgresql \
  --namespace=cortex \
  --set auth.database=cortex \
  --set auth.username=cortex \
  --set persistence.size=50Gi

# Redis (HA mode)
helm install redis bitnami/redis \
  --namespace=cortex \
  --set cluster.enabled=true \
  --set cluster.slaveCount=2 \
  --set persistence.size=10Gi

# ChromaDB
kubectl apply -f deploy/k8s/chromadb-statefulset.yaml
```

### Step 3: Deploy the application

```bash
# Backend API
kubectl apply -f deploy/k8s/backend-deployment.yaml
kubectl apply -f deploy/k8s/backend-service.yaml
kubectl apply -f deploy/k8s/backend-hpa.yaml

# L6 Engine (stateful -- use StatefulSet)
kubectl apply -f deploy/k8s/l6-engine-statefulset.yaml

# Frontend
kubectl apply -f deploy/k8s/frontend-deployment.yaml
kubectl apply -f deploy/k8s/frontend-service.yaml
kubectl apply -f deploy/k8s/frontend-hpa.yaml

# Ingress
kubectl apply -f deploy/k8s/ingress.yaml
```

### Step 4: Verify deployment

```bash
# Check all pods
kubectl get pods -n cortex

# Check services
kubectl get svc -n cortex

# View logs
kubectl logs -n cortex -l app=backend --tail=100

# Port-forward to test locally
kubectl port-forward -n cortex svc/backend 8000:8000
curl http://localhost:8000/api/health
```

---

## 4. Health Monitoring

### Prometheus Metrics

All services expose metrics at `/metrics` (Prometheus format).

**Key metrics to alert on:**

| Metric | Type | Threshold | Severity |
|--------|------|-----------|----------|
| `cortex_pipeline_latency_ms{layer}` | Histogram | p99 > 500ms | Warning |
| `cortex_agent_count` | Gauge | > 90% of max | Warning |
| `cortex_skill_error_rate` | Counter | > 5% in 5m | Critical |
| `cortex_ws_connections` | Gauge | > 1000 | Warning |
| `cortex_api_error_rate` | Counter | > 3% in 1m | Critical |
| `cortex_memory_usage_bytes` | Gauge | > 85% of limit | Critical |
| `cortex_field_entropy` | Gauge | < 0.1 | Info |
| `cortex_l6_scan_duration_ms` | Histogram | p99 > 30s | Warning |

### Grafana Dashboards

Pre-built dashboards are available in `deploy/grafana/dashboards/`:

| Dashboard | Description |
|-----------|-------------|
| `cortex-overview.json` | System-wide health, agent count, throughput |
| `cortex-pipeline.json` | L0--L7 pipeline latency and throughput |
| `cortex-skills.json` | Skill invocation rates and error rates |
| `cortex-l6.json` | L6 module health and events |
| `cortex-resources.json` | Container CPU/memory/network |
| `cortex-market.json` | Market data feed health |

### Alertmanager Rules

Example alert rules (`deploy/prometheus/alert-rules.yaml`):

```yaml
groups:
  - name: cortex-critical
    rules:
      - alert: PipelineStalled
        expr: rate(cortex_pipeline_throughput_hz[5m]) == 0
        for: 30s
        labels: { severity: critical }
        annotations:
          summary: "Pipeline throughput dropped to zero"

      - alert: HighErrorRate
        expr: rate(cortex_api_error_rate[1m]) > 0.03
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "API error rate exceeds 3%"

      - alert: MemoryPressure
        expr: cortex_memory_usage_bytes / cortex_memory_limit_bytes > 0.85
        for: 2m
        labels: { severity: warning }
        annotations:
          summary: "Container memory usage above 85%"
```

---

## 5. Logging and Debugging

### Log Levels

| Level | When to Use |
|-------|-------------|
| `ERROR` | Runtime failures, service degradation |
| `WARNING` | Retryable errors, rate limit hits |
| `INFO` | Lifecycle events, deployments, config changes |
| `DEBUG` | Detailed tracing, request/response dumps |

### Log Format

All services output structured JSON logs:

```json
{
  "timestamp": "2026-06-12T14:30:00.123Z",
  "level": "INFO",
  "service": "backend",
  "trace_id": "tr_abc123",
  "message": "Pipeline stage L4 completed",
  "metadata": {
    "latency_ms": 42.3,
    "layer": "L4",
    "throughput_hz": 9.8
  }
}
```

### Debugging Commands

```bash
# Follow backend logs with grep
kubectl logs -n cortex -l app=backend -f | jq 'select(.level == "ERROR")'

# Check WebSocket connections
kubectl exec -n cortex deploy/backend -- wscount

# Inspect Redis state
kubectl exec -n cortex svc/redis -- redis-cli INFO stats

# Check ChromaDB collections
curl http://localhost:8001/api/v1/collections

# Trigger verbose logging for a specific component
kubectl set env -n cortex deploy/backend LOG_LEVEL=DEBUG
```

### Common Debugging Tools

| Tool | Purpose |
|------|---------|
| `kubectl logs` | Container logs |
| `kubectl exec` | Shell into container |
| `kubectl port-forward` | Local service access |
| `redis-cli` | Inspect Redis state |
| `curl /metrics` | Raw Prometheus metrics |
| `curl /api/health` | System health |

---

## 6. Backup and Restore

### ChromaDB Backup

```bash
# Create backup
kubectl exec -n cortex statefulset/chromadb -- \
  python -c "
import chromadb
client = chromadb.HttpClient(host='localhost', port=8000)
# Backup all collections by exporting to parquet
client.export_collection('skill_vectors', '/backups/skill_vectors_20260612.parquet')
client.export_collection('agent_memory', '/backups/agent_memory_20260612.parquet')
"

# Copy from pod
kubectl cp cortex/chromadb-0:/backups/ ./backups/
```

### PostgreSQL Backup

```bash
# Automated daily backup (cron)
0 3 * * * kubectl exec -n cortex deployment/postgres -- \
  pg_dump -U cortex cortex | gzip > /backups/cortex_$(date +\%Y\%m\%d).sql.gz

# Restore
gunzip -c /backups/cortex_20260612.sql.gz | \
  kubectl exec -n cortex deployment/postgres -i -- \
  psql -U cortex cortex
```

### Redis Backup

```bash
# Trigger RDB snapshot
kubectl exec -n cortex deployment/redis -- redis-cli BGSAVE

# Copy the dump file
kubectl cp cortex/redis-0:/data/dump.rdb ./backups/redis_20260612.rdb
```

### Recovery Procedure

1. Stop all application pods: `kubectl scale deployment -n cortex --replicas=0 --all`
2. Restore PostgreSQL from backup.
3. Restore ChromaDB collections.
4. Restart infrastructure: Redis, PostgreSQL, ChromaDB.
5. Restart application pods: `kubectl scale deployment -n cortex --replicas=3 --all`
6. Verify health: `curl /api/health`

---

## 7. Scaling Guide

| Component | Scale Signal | Scaling Action | Limit |
|-----------|-------------|----------------|-------|
| Frontend | CPU > 70% | Increase replicas | 10 pods |
| Backend | API latency > 200ms p95 | Increase replicas + add Redis | 10 pods |
| L6 Engine | Pipeline queue depth > 100 | Add L6 engine pods | 5 pods |
| ChromaDB | Query latency > 100ms | Increase resources | 8 CPU, 32G RAM |
| Redis | Memory > 80% | Add shards | 6 shards |
| PostgreSQL | Connection count > 80% of max | Add connection pooler (PgBouncer) | -- |

### HPA Configuration Example

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
  namespace: cortex
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## 8. Troubleshooting

### Issue: Backend won't start

```bash
# Check logs
kubectl logs -n cortex deploy/backend

# Common causes:
# - Missing environment variables (HMAC_SECRET_KEY, LLM_API_KEY)
# - PostgreSQL not ready (connection refused)
# - ChromaDB not reachable

# Fix: verify .env or K8s secrets are set correctly
kubectl get secret cortex-secrets -n cortex -o yaml
```

### Issue: WebSocket connections keep disconnecting

```bash
# Check WebSocket count
kubectl exec -n cortex deploy/backend -- wscount

# Check Redis pub/sub channels
kubectl exec -n cortex svc/redis -- redis-cli PUBSUB CHANNELS

# Common causes:
# - Redis connection limit reached
# - Network timeout (check ingress/load balancer settings)
# - Client-side reconnection loop (check browser console)

# Fix: increase maxclients in Redis config
kubectl exec -n cortex svc/redis -- redis-cli CONFIG SET maxclients 5000
```

### Issue: Stigmergy field updates are slow

```bash
# Check field update latency
curl http://localhost:8000/api/health | jq '.field_latency_ms'

# Common causes:
# - Grid size too large (default 64x64)
# - Worker thread pool exhausted
# - PDE solver stuck

# Fix: reduce grid size or increase worker threads
kubectl set env -n cortex deploy/l6-engine FIELD_GRID_SIZE=32 FIELD_WORKERS=4

# Monitor field entropy
curl http://localhost:8000/metrics | grep cortex_field_entropy
```

### Issue: Backtest results don't match expectations

```bash
# Check backtest logs
kubectl logs -n cortex deploy/backend | grep backtest

# Common causes:
# - Data feed has gaps (check market data coverage)
# - Strategy parameters changed during backtest period
# - Commission/slippage model differences

# Fix: verify data completeness
cortex data check --symbol BTC/USD --start 2025-01-01 --end 2026-06-01
```

### Issue: High memory usage in L6 Engine

```bash
# Check memory profile
kubectl top pod -n cortex -l app=l6-engine

# Common causes:
# - Agent memory leak (check agent count growth)
# - Skill cache too large
# - Field grid state accumulation

# Fix: restart the L6 engine pod (safe -- it uses Redis for state)
kubectl rollout restart -n cortex statefulset/l6-engine

# If persistent, increase memory limit:
kubectl set resources -n cortex statefulset/l6-engine \
  --limits=memory=8Gi --requests=memory=4Gi
```

### Quick Reference: Common Commands

```bash
# Restart all services
kubectl rollout restart -n cortex deployment --all

# Scale everything down (maintenance mode)
kubectl scale -n cortex deployment --all --replicas=0

# Scale everything up
kubectl scale -n cortex deployment --all --replicas=3

# Get real-time resource usage
kubectl top pods -n cortex

# Tail all service logs (requires stern)
stern -n cortex .

# Port-forward multiple services
kubectl port-forward -n cortex svc/backend 8000:8000 &
kubectl port-forward -n cortex svc/frontend 3000:3000 &
kubectl port-forward -n cortex svc/grafana 3001:3001 &
```

---

## 9. Security Incident Response

### Incident Levels

| Level | Definition | Response Time |
|-------|-----------|--------------|
| SEV-1 | Active breach, data exfiltration | 15 minutes |
| SEV-2 | Unauthorized access, privilege escalation | 1 hour |
| SEV-3 | Policy violation, misconfiguration | 4 hours |
| SEV-4 | Low-risk vulnerability | 1 week |

### Response Procedure

1. **Identify** -- Check M5 Security Gateway logs for the incident.
2. **Contain** -- Revoke the affected API key: `cortex auth revoke <key_id>`.
3. **Analyze** -- Review audit trail for the affected time window.
4. **Remediate** -- Apply fix, rotate secrets if needed.
5. **Recover** -- Restore from backup if data was corrupted.
6. **Post-mortem** -- Document root cause and preventive measures.

### Key Security Commands

```bash
# List active API keys
cortex auth list-keys

# Revoke a compromised key
cortex auth revoke key_admin_01

# View audit log for a specific actor
curl -H "X-HMAC-Key: $KEY" "$BASE/api/audit?actor=user_suspicious&from=2026-06-12T00:00:00Z"

# Check rate limit violations
curl -H "X-HMAC-Key: $KEY" "$BASE/api/gateway/services" | jq '.data[].blocked_requests'

# Rotate HMAC secret (schedule maintenance window)
kubectl delete secret cortex-secrets -n cortex
kubectl create secret generic cortex-secrets ...  # reapply with new key
kubectl rollout restart -n cortex deployment --all
```

---

## 10. Upgrade Procedures

### Standard Upgrade

```bash
# 1. Pull latest images
docker compose pull

# 2. Apply database migrations (if any)
docker compose run --rm backend alembic upgrade head

# 3. Rolling restart
docker compose up -d

# 4. Verify health
curl http://localhost:8000/api/health
```

### K8s Rolling Upgrade

```bash
# 1. Update image tag in deployment
kubectl set image -n cortex deploy/backend \
  backend=cortex/backend:2.1.0

# 2. Monitor rollout status
kubectl rollout status -n cortex deploy/backend

# 3. If rollout fails, rollback
kubectl rollout undo -n cortex deploy/backend

# 4. Verify after upgrade
kubectl rollout status -n cortex deploy/backend
```

### Upgrade Checklist

- [ ] Database migrations tested on staging
- [ ] ChromaDB schema compatibility verified
- [ ] All 18 mechanisms pass self-test
- [ ] Pipeline E2E test passes on staging
- [ ] Rollback plan documented
- [ ] Monitoring alerts configured for new metrics
- [ ] On-call engineer notified

---

## 11. Related Documents

- [Architecture Overview](./architecture.md) -- system design, pipeline, mechanisms
- [API Reference](./api-reference.md) -- REST and WebSocket endpoint documentation
- [Skill Development Guide](./skill-development-guide.md) -- creating and publishing Skills
