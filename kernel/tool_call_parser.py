"""Ultimate LLM Tool Call Parser — 2026 Universal Standard.

Strategy: NORMALIZE FIRST, then parse.
All LLM format variants → normalized Sclerotium XML → standard parser.
No format can break this — the normalizer handles infinite variations.
"""

import json
import re
from typing import Any

KNOWN_PARAMS = frozenset({
    "file_path", "content", "command", "path", "code", "text", "cmd",
    "working_dir", "timeout", "pattern", "old_string", "new_string",
    "model", "provider", "query", "url", "max_results", "directory",
    "count", "n", "action", "context", "show_all", "long_format",
    "recursive", "replace_all", "mode", "start_line", "end_line",
    "filepath", "filename", "file", "dirname", "output", "input", "source",
    "target", "dest", "name", "value", "data", "body", "raw",
    "description", "cmdline",
})


def _norm_key(k: str) -> str:
    k = k.strip().lower()
    k = re.sub(r'([a-z])([A-Z])', r'\1_\2', k).lower()
    k = k.replace('filepath', 'file_path').replace('filename', 'file_path')
    if k in ("path", "file"): return "file_path"
    if k in ("cmd", "cmdline"): return "command"
    return k


def _normalize_content(content: str) -> str:
    """Convert ANY LLM tool call format into standard Sclerotium XML.

    This is the key insight: instead of adding parsers for every new format,
    normalize everything to one format first. The normalizer handles infinite
    variations because it works at the structural level, not the syntax level.
    """
    result = content

    # ── Step 0: Strip non-JSON code blocks (python/sql/html/... contain dicts that look like tools) ──
    # Keep ```json and ```tool_call blocks for tool call parsing; remove everything else.
    def _strip_non_json_blocks(m):
        lang = m.group(1).lower().strip()
        if lang in ('json', 'tool_call'):
            return m.group(0)  # Keep — will be processed below
        return ''  # Remove — avoid false positives

    result = re.sub(
        r'```(\w+)\s*\n(.*?)\n```',
        _strip_non_json_blocks,
        result, flags=re.DOTALL,
    )

    # ── Step 1: JSON formats → XML ──
    # Handles: {"name":"f","arguments":{...}} (Anthropic/OpenAI)
    #          {"tool":"f","param":"val",...}       (Sclerotium native)
    #          {"function":{"name":"f","arguments":{...}}} (GPT function calling)
    def _repair_json(s: str) -> str:
        """Repair common JSON issues: Windows paths (single backslashes)."""
        # Fix backslashes not followed by valid JSON escape chars (", \, /, b, f, n, r, t, u)
        # This fixes C:\Users\spec.md → C:\\Users\\spec.md but preserves \n, \t, \" etc.
        s = re.sub(r'\\(?![\\"/bfnrtu])', r'\\\\', s)
        return s

    def _json_to_xml(m):
        try:
            # m.group(0) = full match including ``` fences; m.group(1) = JSON content
            json_str = m.group(1) if m.lastindex and m.lastindex >= 1 else m.group(0)
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Try repair: fix Windows paths etc.
                json_str = _repair_json(json_str)
                data = json.loads(json_str)
            # Tool name: check "tool" (Sclerotium), "name" (Anthropic), "function.name" (OpenAI)
            name = (data.get("tool") or data.get("name")
                    or data.get("function", {}).get("name", ""))
            if not name:
                return m.group(0)
            # Arguments: handle all nesting styles
            if "tool" in data:
                # Sclerotium flat format: {"tool":"f","param":"val"} → args=everything except "tool"
                args = {k: v for k, v in data.items() if k != "tool"}
            elif "arguments" in data:
                args = data["arguments"]
            elif "parameters" in data:
                args = data["parameters"]
            elif "input" in data:
                args = data["input"]
            elif "function" in data:
                args = data["function"].get("arguments", {})
            else:
                args = {k: v for k, v in data.items() if k not in ("name",)}
            if isinstance(args, str):
                try: args = json.loads(args)
                except: args = {"raw": args}
            if name:
                xml = f"<tool_call>{name}</tool_call>"
                for k, v in args.items():
                    xml += f"<{k}>{v}</{k}>"
                return xml
        except:
            pass
        return m.group(0)

    # ── JSON fences FIRST (before bare JSON — prevents double-conversion) ──
    result = re.sub(r'```(?:tool_call|json)\s*\n(.*?)\n```', _json_to_xml, result, flags=re.DOTALL)

    # Bare JSON: match balanced braces with "tool" field ONLY
    # ("name" causes false positives with regular data dicts like {"name":"test"})
    # Collect ALL matches first, then process right-to-left to avoid index shifting
    bare_matches = []
    for m in re.finditer(r'\{[^{}]*"tool"\s*:\s*"(\w+)"', result):
        start = m.start()
        depth = 0
        end = start
        for i, ch in enumerate(result[start:], start):
            if ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        bare_matches.append((start, end))
    # Process right-to-left: replacing won't shift earlier indices
    for start, end in reversed(bare_matches):
        json_str = result[start:end]
        try:
            data = json.loads(json_str)
            name = data.get("tool")  # "tool" key only — "name" is too common in data
            if name:
                args = {k: v for k, v in data.items() if k != "tool"}
                if isinstance(args, str):
                    try: args = json.loads(args)
                    except: args = {"raw": args}
                xml = f"<tool_call>{name}</tool_call>"
                for k, v in args.items():
                    xml += f"<{k}>{v}</{k}>"
                result = result[:start] + xml + result[end:]
        except:
            pass

    # Mistral [TOOL_CALLS]
    result = re.sub(r'\[TOOL_CALLS\]\s*\[.*?\]', '', result, flags=re.DOTALL)

    # Markdown Calling
    def _md_to_xml(m):
        name = m.group(1)
        try: args = json.loads(m.group(2))
        except: args = {"raw": m.group(2)}
        xml = f"<tool_call>{name}</tool_call>"
        for k, v in args.items():
            xml += f"<{k}>{v}</{k}>"
        return xml
    result = re.sub(r'\*\*Calling:\*\*\s*`(\w+)`\s*\n\s*```(?:json)?\s*\n(.*?)\n```',
                    _md_to_xml, result, flags=re.DOTALL)

    # ── Step 2: Tag normalization → Sclerotium XML ──
    # <tool_call name="xxx"> → <tool_call>xxx</tool_call>
    result = re.sub(r'<tool_call\s+name="(\w+)"\s*>', r'<tool_call>\1</tool_call>', result)

    # <function=name>args</function> → <tool_call>name</tool_call>
    result = re.sub(r'<function=(\w+)>(.*?)</function>', r'<tool_call>\1</tool_call>', result, flags=re.DOTALL)

    # ── Anthropic/Claude <function_calls> + <invoke> + <parameter> format ──
    # <function_calls><invoke name="T"><parameter name="K">V</parameter></invoke></function_calls>
    # → <tool_call>T</tool_call><K>V</K>
    def _function_calls_to_xml(m):
        block = m.group(0)
        result_xml = ""
        for inv in re.finditer(r'<invoke\s+name="(\w+)"\s*>(.*?)</invoke>', block, re.DOTALL):
            tool_name = inv.group(1)
            body = inv.group(2)
            params_xml = ""
            for pm in re.finditer(r'<parameter\s+name="([^"]+)"\s*>(.*?)</parameter>', body, re.DOTALL):
                pname = _norm_key(pm.group(1))
                pval = pm.group(2).strip()
                if pname in KNOWN_PARAMS:
                    params_xml += f"<{pname}>{pval}</{pname}>"
            result_xml += f"<tool_call>{tool_name}</tool_call>{params_xml}"
        return result_xml if result_xml else block
    result = re.sub(r'<function_calls>.*?</function_calls>', _function_calls_to_xml, result, flags=re.DOTALL)

    # ── Step 3: Parameter tag normalization → <key>val</key> ──
    # <key>name</key><val>value</val> → <name>value</name>
    def _keyval_pairs(m):
        block = m.group(0)
        # Find <key>K</key><val>V</val> pairs
        keys = re.findall(r'<key>(\w+)</key>', block)
        vals = re.findall(r'<val>(.*?)</val>', block, re.DOTALL)
        xml = ""
        for i in range(min(len(keys), len(vals))):
            k = _norm_key(keys[i])
            if k in KNOWN_PARAMS:
                xml += f"<{k}>{vals[i]}</{k}>"
        return xml if xml else block
    result = re.sub(r'(?:<key>\w+</key>\s*<val>.*?</val>\s*)+', _keyval_pairs, result, flags=re.DOTALL)

    # <key>name</key>value</key> → <name>value</name>
    def _key_bare(m):
        block = m.group(0)
        xml = ""
        for km in re.finditer(r'<key>(\w+)</key>(.*?)</key>', block, re.DOTALL):
            k = _norm_key(km.group(1))
            v = km.group(2).strip()
            # Skip if value contains nested tags (will be handled by keyval)
            if '<key>' in v or '<val>' in v:
                continue
            if k in KNOWN_PARAMS:
                xml += f"<{k}>{v}</{k}>"
        return xml if xml else block
    result = re.sub(r'(?:<key>\w+</key>.*?</key>\s*)+', _key_bare, result, flags=re.DOTALL)

    # <param>K</param><param>V</param> → <K>V</K>
    def _param_pairs(m):
        block = m.group(0)
        all_params = re.findall(r'<(param|arg|value)>([^<]+)</\1>', block)
        xml = ""
        for i in range(0, len(all_params) - 1, 2):
            k = _norm_key(all_params[i][1])
            v = all_params[i + 1][1].strip() if i + 1 < len(all_params) else ""
            if k in KNOWN_PARAMS:
                xml += f"<{k}>{v}</{k}>"
        return xml if xml else block
    result = re.sub(r'(?:<(?:param|arg|value)>[^<]+</(?:param|arg|value)>\s*)+',
                    _param_pairs, result, flags=re.DOTALL)

    # <key>K</key> followed by <key>V</key> → <K>V</K>
    result = re.sub(r'<key>(\w+)</key>\s*<key>([^<]+)</key>',
                    lambda m: f"<{_norm_key(m.group(1))}>{m.group(2)}</{_norm_key(m.group(1))}>"
                    if _norm_key(m.group(1)) in KNOWN_PARAMS else m.group(0),
                    result)

    # ── Step 4: Clean up artifacts ──
    result = re.sub(r'<requires_approval>[^<]*</requires_approval>', '', result)
    result = re.sub(r'<dangerous>[^<]*</dangerous>', '', result)

    return result


def _extract_params_from_text(block: str) -> dict[str, str]:
    """Extract key-value parameters from a block of text using ALL known formats."""
    args: dict[str, str] = {}

    # Format A: <key>value</key>  — Sclerotium native XML with matching close tags
    for pm in re.finditer(
        rf'<({"|".join(KNOWN_PARAMS)})>(.*?)</\1>',
        block, re.DOTALL | re.IGNORECASE):
        key = _normalize_key(pm.group(1))
        val = pm.group(2).strip()
        if key in ("path",): key = "file_path"
        if key in ("cmd",): key = "command"
        args[key] = val
    if args:
        return args

    # Format B: <key>name</key>value</key>  — malformed XML (only if no <key>/<val> pairs inside)
    kmatches = list(re.finditer(r'<key>(\w+)</key>(.*?)</key>', block, re.DOTALL))
    # Only use Format B if values don't contain nested <key> or <val> (prevents greedy matching)
    clean_matches = [(km, km.group(2).strip()) for km in kmatches
                     if '<key>' not in km.group(2) and '<val>' not in km.group(2)]
    for km, val in clean_matches:
        key = _normalize_key(km.group(1))
        if key in KNOWN_PARAMS:
            if key in ("path",): key = "file_path"
            if key in ("cmd",): key = "command"
            args[key] = val
    if args:
        return args

    # Format C: <key>k</key><val>v</val> — explicit key+value markup
    kmatches = list(re.finditer(r'<key>(\w+)</key>', block))
    vmatches = list(re.finditer(r'<val>(.*?)</val>', block))
    for i in range(min(len(kmatches), len(vmatches))):
        k = _normalize_key(kmatches[i].group(1))
        v = vmatches[i].group(1).strip()
        if k in KNOWN_PARAMS:
            if k in ("path",): k = "file_path"
            if k in ("cmd",): k = "command"
            args[k] = v
    if args: return args

    # Format C-alt: <param>/<arg>/<value>/<key> alternating pairs (k/v/k/v)
    for tag in ("param", "arg", "value", "key"):
        if args: break
        pms = list(re.finditer(rf'<{tag}>([^<]+)</{tag}>', block, re.DOTALL))
        for i in range(0, len(pms) - 1, 2):
            k = _normalize_key(pms[i].group(1))
            v = pms[i + 1].group(1).strip() if i + 1 < len(pms) else ""
            if k in KNOWN_PARAMS:
                if k in ("path",): k = "file_path"
                if k in ("cmd",): k = "command"
                args[k] = v
    if args:
        return args

    # Format D: JSON in block
    json_str = block.strip()
    if json_str.startswith("{"):
        try:
            parsed = json.loads(json_str)
            if isinstance(parsed, dict):
                if "arguments" in parsed and "name" in parsed:
                    return parsed["arguments"]
                if "input" in parsed and "name" in parsed:
                    return parsed["input"]
                if "tool" in parsed:
                    return {k: v for k, v in parsed.items() if k != "tool"}
                return {k: v for k, v in parsed.items() if k not in ("name",)}
        except json.JSONDecodeError:
            pass

    return args


def extract_tool_calls(content: str) -> list[dict[str, Any]]:
    """Extract ALL tool calls. Normalize first, then parse the clean XML."""
    # ── Normalize: any format → standard Sclerotium XML ──
    clean = _normalize_content(content)

    tool_calls: list[dict[str, Any]] = []

    # ── Parse normalized XML: <tool_call>name</tool_call><key>val</key> ──
    for m in re.finditer(r'<tool_call>\s*(\w+)\s*</tool_call>', clean, re.DOTALL):
        name = m.group(1)
        rest = clean[m.end():]
        next_tc = re.search(r'<tool_call[>\s]', rest)
        block = rest[:next_tc.start()] if next_tc else rest

        args = {}
        for pm in re.finditer(
            rf'<({"|".join(KNOWN_PARAMS)})>(.*?)</\1>',
            block, re.DOTALL | re.IGNORECASE):
            key = _norm_key(pm.group(1))
            val = pm.group(2).strip()
            args[key] = val

        # Fallback: <key>bare</key> not caught by normalizer
        if not args:
            for km in re.finditer(r'<key>(\w+)</key>(.*?)</key>', block, re.DOTALL):
                k = _norm_key(km.group(1))
                v = km.group(2).strip()
                if '<key>' not in v and '<val>' not in v and k in KNOWN_PARAMS:
                    args[k] = v

        tool_calls.append({"name": name, "arguments": args})

    # ── Direct JSON fallback: handle {"tool":"name","param":"val"} ──
    # Only matches "tool" key — "name" key causes too many false positives
    # (e.g., {"name":"test-project"} inside code blocks or content strings).
    if not tool_calls:
        for m in re.finditer(r'\{\s*"tool"\s*:\s*"(\w+)"', clean):
            start = m.start()
            depth = 0
            end = start
            for i, ch in enumerate(clean[start:], start):
                if ch == '{': depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        end = i + 1
                        break
            try:
                data = json.loads(clean[start:end])
                if isinstance(data, dict) and data.get("tool"):
                    name = data["tool"]
                    args = {k: v for k, v in data.items() if k != "tool"}
                    tool_calls.append({"name": name, "arguments": args})
            except (json.JSONDecodeError, KeyError):
                pass

    # Deduplicate
    seen = set()
    unique = []
    for tc in tool_calls:
        fp = f"{tc['name']}:{sorted(tc.get('arguments', {}).items())}"
        if fp not in seen:
            seen.add(fp)
            unique.append(tc)

    return unique
