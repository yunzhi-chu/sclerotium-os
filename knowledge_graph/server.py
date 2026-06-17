"""Trinity Knowledge Graph Server — serves full codegraph data (117K nodes, 298K edges).

Usage:
    python server.py [--port 8899]

Endpoints:
    GET /           — Interactive G6 v5 WebGL visualization
    GET /api/stats  — Graph statistics summary
    GET /api/nodes  — All nodes (compact JSON)
    GET /api/edges  — All edges (compact JSON)
    GET /api/graph  — Full graph in one call (nodes + edges)
    GET /api/clusters — Pre-computed file-level clusters for LOD
"""

from __future__ import annotations

import gzip
import json
import os
import sqlite3
import sys
import time
from collections import defaultdict
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ── Configuration ────────────────────────────────────────────
ROOT = Path(__file__).parent.resolve()
DATABASES = {
    "sclerotium-os": Path(r"C:\Users\34442\Desktop\porject\Quantitative model\sclerotium-os\.codegraph\codegraph.db"),
    "fungal-cortex": Path(r"C:\Users\34442\Desktop\porject\Quantitative model\fungal-cortex\.codegraph\codegraph.db"),
    "mirofish": Path(r"C:\Users\34442\Desktop\porject\Quantitative model\MiroFish-main\.codegraph\codegraph.db"),
}

# Color mapping for node kinds
KIND_COLORS = {
    "function": "#7c3aed", "method": "#a78bfa", "class": "#f59e0b",
    "interface": "#fbbf24", "variable": "#00d4aa", "constant": "#34d399",
    "import": "#6b7280", "file": "#4b5563", "route": "#ff6b6b",
    "module": "#00bcd4", "type": "#ec4899",
}

# Color mapping for edge kinds
EDGE_KINDS = {
    "calls": "calls", "contains": "contains", "imports": "imports",
    "instantiates": "instantiates", "references": "references",
    "extends": "extends", "decorates": "decorates", "implements": "implements",
}

# ── Cache ────────────────────────────────────────────────────
_cache: dict = {}  # In-memory cache for graph data


def _load_all_data() -> dict:
    """Extract all nodes and edges from the 3 codegraph databases."""
    if _cache:
        return _cache

    all_nodes = []
    all_edges = []
    node_id_counter = 0
    node_id_map: dict[str, str] = {}  # (system, original_id) -> global_id
    stats = {"systems": {}, "total_nodes": 0, "total_edges": 0}

    for system_name, db_path in DATABASES.items():
        if not db_path.exists():
            print(f"[WARN] DB not found: {db_path}")
            continue

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row

        # Load nodes
        sys_nodes = []
        for row in conn.execute("SELECT id, kind, name, file_path, language, start_line FROM nodes"):
            global_id = f"{system_name}:{row['id']}"
            node_id_map[(system_name, row["id"])] = global_id
            # Extract file name from path
            file_name = row["file_path"].replace("\\", "/").split("/")[-1] if row["file_path"] else "?"
            sys_nodes.append({
                "id": global_id,
                "label": row["name"][:60] if row["name"] else "?",
                "kind": row["kind"] or "unknown",
                "file": file_name,
                "lang": row["language"] or "py",
                "line": row["start_line"] or 0,
                "system": system_name,
                "color": KIND_COLORS.get(row["kind"], "#6b7280"),
            })

        # Load edges
        sys_edges = []
        for row in conn.execute("SELECT source, target, kind FROM edges WHERE source IS NOT NULL AND target IS NOT NULL"):
            src_gid = node_id_map.get((system_name, row["source"]))
            tgt_gid = node_id_map.get((system_name, row["target"]))
            if src_gid and tgt_gid:
                sys_edges.append({
                    "source": src_gid,
                    "target": tgt_gid,
                    "kind": row["kind"] or "reference",
                })

        conn.close()

        stats["systems"][system_name] = {
            "nodes": len(sys_nodes), "edges": len(sys_edges),
            "db_path": str(db_path),
        }
        all_nodes.extend(sys_nodes)
        all_edges.extend(sys_edges)
        print(f"[LOAD] {system_name}: {len(sys_nodes)} nodes, {len(sys_edges)} edges")

    stats["total_nodes"] = len(all_nodes)
    stats["total_edges"] = len(all_edges)

    # Pre-compute clusters (by file + first directory)
    clusters = defaultdict(lambda: {"nodes": [], "label": "", "system": ""})
    for n in all_nodes:
        key = n["file"]
        clusters[key]["nodes"].append(n["id"])
        clusters[key]["label"] = n["file"]
        clusters[key]["system"] = n["system"]

    # Convert clusters to list, filter small ones
    cluster_list = [
        {"id": f"cluster:{k}", "label": v["label"], "system": v["system"],
         "nodeCount": len(v["nodes"]), "nodes": v["nodes"]}
        for k, v in sorted(clusters.items(), key=lambda x: -len(x[1]["nodes"]))
        if len(v["nodes"]) >= 3  # Only show clusters with 3+ nodes
    ]

    _cache["nodes"] = all_nodes
    _cache["edges"] = all_edges
    _cache["stats"] = stats
    _cache["clusters"] = cluster_list
    _cache["loaded_at"] = time.time()
    return _cache


# ── JSON encoder for compact output ─────────────────────────
class CompactEncoder(json.JSONEncoder):
    def default(self, obj):
        return str(obj)


def _json_response(data, handler, compress=True):
    """Send JSON response with optional gzip compression."""
    body = json.dumps(data, cls=CompactEncoder, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    # Check for gzip support
    accept_encoding = handler.headers.get("Accept-Encoding", "")
    if compress and "gzip" in accept_encoding and len(body) > 1024:
        body = gzip.compress(body, compresslevel=6)
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Encoding", "gzip")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Cache-Control", "public, max-age=3600")
        handler.end_headers()
        handler.wfile.write(body)
    else:
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Cache-Control", "public, max-age=3600")
        handler.end_headers()
        handler.wfile.write(body)


# ── HTTP Handler ─────────────────────────────────────────────
class GraphServer(SimpleHTTPRequestHandler):
    """Custom handler that serves the graph API + static files."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # API routes
        if path == "/api/stats":
            data = _load_all_data()
            return _json_response(data["stats"], self)

        if path == "/api/nodes":
            data = _load_all_data()
            system = params.get("system", [None])[0]
            kind = params.get("kind", [None])[0]
            limit = int(params.get("limit", [0])[0]) or None
            nodes = data["nodes"]
            if system:
                nodes = [n for n in nodes if n["system"] == system]
            if kind:
                nodes = [n for n in nodes if n["kind"] == kind]
            if limit:
                nodes = nodes[:limit]
            return _json_response({"nodes": nodes, "count": len(nodes)}, self)

        if path == "/api/edges":
            data = _load_all_data()
            limit = int(params.get("limit", [0])[0]) or None
            edges = data["edges"][:limit] if limit else data["edges"]
            return _json_response({"edges": edges, "count": len(edges)}, self)

        if path == "/api/graph":
            data = _load_all_data()
            nodes_only = "nodes" in params
            edges_only = "edges" in params
            result = {}
            if not edges_only:
                result["nodes"] = data["nodes"]
            if not nodes_only:
                result["edges"] = data["edges"]
            if not nodes_only and not edges_only:
                result["stats"] = data["stats"]
                result["clusters"] = data["clusters"]
            return _json_response(result, self)

        if path == "/api/clusters":
            data = _load_all_data()
            return _json_response({"clusters": data["clusters"]}, self)

        if path == "/api/health":
            data = _load_all_data()
            stats = data["stats"]
            return _json_response({
                "status": "ok",
                "total_nodes": stats["total_nodes"],
                "total_edges": stats["total_edges"],
                "systems": list(stats["systems"].keys()),
                "loaded_at": data.get("loaded_at", 0),
            }, self)

        # Serve static files (index.html, etc.)
        if path == "/" or path == "":
            self.path = "/index.html"

        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Accept-Encoding")
        self.end_headers()

    def log_message(self, format, *args):
        # Suppress default logging for API calls
        if "/api/" in str(args[0]) and "200" in str(format % args):
            return
        super().log_message(format, *args)


# ── Main ─────────────────────────────────────────────────────
def main():
    import argparse
    # Fix Windows console encoding for emoji
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description="Trinity Knowledge Graph Server")
    parser.add_argument("--port", type=int, default=8899, help="Server port (default: 8899)")
    parser.add_argument("--preload", action="store_true", help="Preload all data on startup")
    args = parser.parse_args()

    # Preload data
    if args.preload:
        print("[INIT] Preloading graph data from 3 databases...")
        t0 = time.time()
        _load_all_data()
        print(f"[INIT] Loaded in {time.time() - t0:.1f}s")

    # Start server
    server = HTTPServer(("0.0.0.0", args.port), GraphServer)
    print(f"\n{'='*60}")
    print(f"[Trinity] Knowledge Graph Server")
    print(f"  http://localhost:{args.port}")
    print(f"  API: http://localhost:{args.port}/api/health")
    print(f"  Data: {_cache.get('stats', {}).get('total_nodes', '?')} nodes, "
          f"{_cache.get('stats', {}).get('total_edges', '?')} edges")
    print(f"  (Data loads on first API request if not preloaded)")
    print(f"{'='*60}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server stopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
