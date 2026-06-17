"use client";

import { useMemo, useState, useCallback } from "react";
import { useL6Store } from "@/stores/l6-store";
import {
  SCAN_DIMENSION_LABELS,
  type ArchitectureIssue,
  type ScanDimension,
} from "@/types/l6";

type Severity = ArchitectureIssue["severity"];

const SEVERITY_ORDER: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const SEVERITY_BG: Record<Severity, string> = {
  critical: "bg-[#ef4444]",
  high: "bg-[#f59e0b]",
  medium: "bg-[#3b82f6]",
  low: "bg-[#6b7280]",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Open",
  in_progress: "In Progress",
  fixed: "Fixed",
  approved: "Approved",
  rejected: "Rejected",
};

const STATUS_COLORS: Record<string, string> = {
  open: "#f59e0b",
  in_progress: "#3b82f6",
  fixed: "#22c55e",
  approved: "#00d4aa",
  rejected: "#ef4444",
};

interface FilterOption {
  label: string;
  value: Severity | "all";
}

const FILTERS: FilterOption[] = [
  { label: "All", value: "all" },
  { label: "Critical", value: "critical" },
  { label: "High", value: "high" },
  { label: "Medium", value: "medium" },
  { label: "Low", value: "low" },
];

const DIMENSION_COLORS: Record<ScanDimension, string> = {
  redundancy: "#8b5cf6",
  coupling: "#ec4899",
  latency: "#f59e0b",
  algorithm_gap: "#3b82f6",
  skill_gap: "#00d4aa",
  bottleneck: "#ef4444",
  dead_code: "#6b7280",
  error_pattern: "#f97316",
};

interface IssueCardProps {
  issue: ArchitectureIssue;
}

function IssueCard({ issue }: IssueCardProps) {
  const [expanded, setExpanded] = useState(false);

  const toggleExpanded = useCallback(() => setExpanded((e) => !e), []);
  const maxDescLen = 120;
  const shouldTruncate = issue.description.length > maxDescLen;
  const displayDesc =
    shouldTruncate && !expanded
      ? issue.description.slice(0, maxDescLen) + "..."
      : issue.description;

  return (
    <div className="rounded-lg border border-cortex-border bg-[#0f0f20] mb-2 overflow-hidden">
      <div className="p-3">
        {/* Severity dot + title row */}
        <div className="flex items-start gap-2.5 mb-1.5">
          <span
            className={`w-2.5 h-2.5 rounded-full mt-1 shrink-0 ${SEVERITY_BG[issue.severity]}`}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-white truncate">
                {issue.title}
              </span>
              {issue.auto_fixable && (
                <span className="px-1 py-0.5 rounded bg-[#00d4aa]/15 text-[#00d4aa] text-[8px] font-mono font-bold">
                  AUTO-FIX
                </span>
              )}
              <span
                className="px-1 py-0.5 rounded text-[8px] font-mono font-bold"
                style={{
                  backgroundColor: `${STATUS_COLORS[issue.status]}22`,
                  color: STATUS_COLORS[issue.status],
                }}
              >
                {STATUS_LABELS[issue.status] ?? issue.status}
              </span>
            </div>
            <span className="text-[10px] text-gray-500 font-mono">
              {issue.dimension.replace(/_/g, " ")}
            </span>
          </div>
        </div>

        {/* Description */}
        <p className="text-[12px] text-gray-400 leading-relaxed mb-2">{displayDesc}</p>
        {shouldTruncate && (
          <button
            onClick={toggleExpanded}
            className="text-[10px] text-cortex-primary hover:underline font-mono mb-2"
          >
            {expanded ? "show less" : "show more"}
          </button>
        )}

        {/* Expanded details */}
        {expanded && (
          <div className="mt-2 pt-2 border-t border-cortex-border space-y-2">
            {issue.source_file && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-500">File:</span>
                <span className="text-[10px] font-mono text-gray-300">
                  {issue.source_file}
                  {issue.line_range &&
                    `:${issue.line_range[0]}-${issue.line_range[1]}`}
                </span>
              </div>
            )}
            {issue.suggestion && (
              <div className="bg-[#141428] rounded p-2">
                <span className="text-[10px] text-gray-500 block mb-1">Suggestion:</span>
                <span className="text-[10px] text-gray-300 font-mono">
                  {issue.suggestion}
                </span>
              </div>
            )}
            <div className="flex items-center gap-2 text-[10px] text-gray-500 font-mono">
              <span>
                Created: {new Date(issue.created_at).toLocaleString()}
              </span>
              {issue.fixed_at && (
                <span>
                  | Fixed: {new Date(issue.fixed_at).toLocaleString()}
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface DimensionGroupProps {
  dimension: ScanDimension;
  issues: ArchitectureIssue[];
}

function DimensionGroup({ dimension, issues }: DimensionGroupProps) {
  const [collapsed, setCollapsed] = useState(false);
  const toggle = useCallback(() => setCollapsed((c) => !c), []);
  const dimColor = DIMENSION_COLORS[dimension];

  const criticalCount = issues.filter((i) => i.severity === "critical").length;

  return (
    <div className="mb-3">
      {/* Section header */}
      <button
        onClick={toggle}
        className="flex items-center justify-between w-full py-2 px-1 rounded hover:bg-[#1a1a35] transition-colors"
      >
        <div className="flex items-center gap-2">
          <div
            className="w-1 h-4 rounded-full"
            style={{ backgroundColor: dimColor }}
          />
          <span className="text-xs font-semibold text-gray-300">
            {SCAN_DIMENSION_LABELS[dimension]}
          </span>
          <span className="text-[10px] font-mono text-gray-500">
            ({issues.length})
          </span>
          {criticalCount > 0 && (
            <span className="px-1 py-0.5 rounded bg-[#ef4444]/20 text-[#ef4444] text-[8px] font-mono font-bold">
              {criticalCount} critical
            </span>
          )}
        </div>
        <svg
          className={`w-3 h-3 text-gray-500 transition-transform duration-150 ${
            collapsed ? "" : "rotate-180"
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
        </svg>
      </button>

      {/* Issues list */}
      {!collapsed && (
        <div className="mt-1 pl-2">
          {issues.map((issue) => (
            <IssueCard key={issue.id} issue={issue} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function IssueList() {
  const issues = useL6Store((s) => s.issues);
  const issueFilter = useL6Store((s) => s.issueFilter);
  const setIssueFilter = useL6Store((s) => s.setIssueFilter);

  const currentFilter = (issueFilter ?? "all") as Severity | "all";

  const filteredIssues = useMemo(() => {
    if (currentFilter === "all") return issues;
    return issues.filter((i) => i.severity === currentFilter);
  }, [issues, currentFilter]);

  const groupedIssues = useMemo(() => {
    const groups = new Map<ScanDimension, ArchitectureIssue[]>();
    for (const issue of filteredIssues) {
      const existing = groups.get(issue.dimension);
      if (existing) {
        existing.push(issue);
      } else {
        groups.set(issue.dimension, [issue]);
      }
    }
    // Sort groups by most severe issue in each
    const sorted = Array.from(groups.entries()).sort((a, b) => {
      const minA = Math.min(...a[1].map((i) => SEVERITY_ORDER[i.severity]));
      const minB = Math.min(...b[1].map((i) => SEVERITY_ORDER[i.severity]));
      return minA - minB;
    });
    return sorted;
  }, [filteredIssues]);

  const flatIssues = useMemo(() => {
    return filteredIssues.sort(
      (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
    );
  }, [filteredIssues]);

  const isEmpty = issues.length === 0;
  const isFilteredEmpty = !isEmpty && flatIssues.length === 0;

  return (
    <div className="rounded-xl border border-cortex-border bg-cortex-surface overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cortex-border">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Architecture Issues
          </h3>
          <span className="text-[10px] font-mono text-gray-500">
            {issues.length} total
          </span>
        </div>

        {/* Filter buttons */}
        <div className="flex gap-1.5 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setIssueFilter(f.value === "all" ? null : f.value)}
              className={[
                "px-2.5 py-1 rounded text-[10px] font-mono font-medium",
                "transition-all duration-150",
                currentFilter === f.value ||
                  (currentFilter === null && f.value === "all")
                  ? "bg-cortex-primary/20 text-cortex-primary border border-cortex-primary/30"
                  : "bg-[#1a1a35] text-gray-500 border border-transparent hover:bg-[#2a2a4a] hover:text-gray-300",
              ].join(" ")}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content area */}
      <div className="p-4">
        {/* Empty state */}
        {isEmpty && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <svg
              className="w-12 h-12 text-[#22c55e] mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm text-gray-400 font-semibold">
              No issues detected
            </span>
            <span className="text-[11px] text-gray-500 mt-1">
              System architecture is healthy
            </span>
          </div>
        )}

        {/* Filtered empty state */}
        {isFilteredEmpty && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <svg
              className="w-8 h-8 text-gray-600 mb-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-xs text-gray-500">
              No {currentFilter} severity issues
            </span>
          </div>
        )}

        {/* Grouped view */}
        {!isEmpty && !isFilteredEmpty && (
          <div>
            {groupedIssues.map(([dimension, dimIssues]) => (
              <DimensionGroup
                key={dimension}
                dimension={dimension}
                issues={dimIssues}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
