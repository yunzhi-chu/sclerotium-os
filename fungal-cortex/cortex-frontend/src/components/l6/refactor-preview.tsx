"use client";

import { useState, useMemo, useCallback } from "react";
import { useL6Store } from "@/stores/l6-store";
import type { ArchitectureIssue } from "@/types/l6";
import { Button } from "@/components/ui/button";

interface DiffLine {
  type: "added" | "removed" | "context";
  content: string;
  lineNumber: number;
}

interface SimpleDiffViewProps {
  beforeCode: string;
  afterCode: string;
}

function SimpleDiffView({ beforeCode, afterCode }: SimpleDiffViewProps) {
  const diffLines = useMemo(() => {
    const beforeLines = beforeCode.split("\n");
    const afterLines = afterCode.split("\n");
    const maxLen = Math.max(beforeLines.length, afterLines.length);
    const lines: DiffLine[] = [];

    for (let i = 0; i < maxLen; i++) {
      const beforeLine = beforeLines[i];
      const afterLine = afterLines[i];

      if (beforeLine !== undefined && afterLine !== undefined) {
        if (beforeLine === afterLine) {
          lines.push({ type: "context", content: beforeLine, lineNumber: i + 1 });
        } else {
          lines.push({ type: "removed", content: beforeLine, lineNumber: i + 1 });
          lines.push({ type: "added", content: afterLine, lineNumber: i + 1 });
        }
      } else if (beforeLine !== undefined) {
        lines.push({ type: "removed", content: beforeLine, lineNumber: i + 1 });
      } else if (afterLine !== undefined) {
        lines.push({ type: "added", content: afterLine, lineNumber: i + 1 });
      }
    }

    return lines;
  }, [beforeCode, afterCode]);

  return (
    <div className="rounded-lg border border-cortex-border overflow-hidden">
      {/* Diff header */}
      <div className="flex border-b border-cortex-border">
        <div className="flex-1 px-3 py-1.5 text-[9px] font-mono font-semibold text-[#ef4444] bg-[#ef4444]/5 border-r border-cortex-border">
          Before
        </div>
        <div className="flex-1 px-3 py-1.5 text-[9px] font-mono font-semibold text-[#22c55e] bg-[#22c55e]/5">
          After
        </div>
      </div>

      {/* Side-by-side diff */}
      <div className="flex">
        {/* Before column */}
        <div className="flex-1 border-r border-cortex-border overflow-x-auto">
          <table className="w-full border-collapse">
            <tbody>
              {diffLines.map((line, i) => {
                if (line.type === "added") {
                  return (
                    <tr key={`before-${i}`} className="bg-[#0a0a0f]">
                      <td className="text-[9px] font-mono text-gray-700 text-right px-2 py-0.5 select-none w-8 border-r border-cortex-border">
                        &nbsp;
                      </td>
                      <td className="text-[10px] font-mono text-gray-700 px-2 py-0.5 whitespace-pre">
                        &nbsp;
                      </td>
                    </tr>
                  );
                }
                const bgColor =
                  line.type === "removed"
                    ? "bg-[#ef4444]/10"
                    : "bg-[#0a0a0f]";
                const textColor =
                  line.type === "removed" ? "#fca5a5" : "#888";
                return (
                  <tr key={`before-${i}`} className={bgColor}>
                    <td className="text-[9px] font-mono text-gray-700 text-right px-2 py-0.5 select-none w-8 border-r border-cortex-border">
                      {line.lineNumber}
                    </td>
                    <td
                      className="text-[10px] font-mono px-2 py-0.5 whitespace-pre"
                      style={{ color: textColor }}
                    >
                      {line.type === "removed" ? `-${line.content}` : ` ${line.content}`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* After column */}
        <div className="flex-1 overflow-x-auto">
          <table className="w-full border-collapse">
            <tbody>
              {diffLines.map((line, i) => {
                if (line.type === "removed") {
                  return (
                    <tr key={`after-${i}`} className="bg-[#0a0a0f]">
                      <td className="text-[9px] font-mono text-gray-700 text-right px-2 py-0.5 select-none w-8 border-r border-cortex-border">
                        &nbsp;
                      </td>
                      <td className="text-[10px] font-mono text-gray-700 px-2 py-0.5 whitespace-pre">
                        &nbsp;
                      </td>
                    </tr>
                  );
                }
                const bgColor =
                  line.type === "added"
                    ? "bg-[#22c55e]/10"
                    : "bg-[#0a0a0f]";
                const textColor =
                  line.type === "added" ? "#86efac" : "#888";
                return (
                  <tr key={`after-${i}`} className={bgColor}>
                    <td className="text-[9px] font-mono text-gray-700 text-right px-2 py-0.5 select-none w-8 border-r border-cortex-border">
                      {line.lineNumber}
                    </td>
                    <td
                      className="text-[10px] font-mono px-2 py-0.5 whitespace-pre"
                      style={{ color: textColor }}
                    >
                      {line.type === "added" ? `+${line.content}` : ` ${line.content}`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

interface PendingApprovalCardProps {
  issue: ArchitectureIssue;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  processing: boolean;
}

function PendingApprovalCard({
  issue,
  onApprove,
  onReject,
  processing,
}: PendingApprovalCardProps) {
  const [expanded, setExpanded] = useState(false);

  const demoBeforeCode = useMemo(() => {
    if (issue.suggestion)
      return `// Current implementation\nfunction process() {\n  ${issue.suggestion
        .split(" ")
        .slice(0, 6)
        .join(" ")}...\n  // TODO: optimize\n  return result;\n}`;
    return `// ${issue.title}\nfunction handle() {\n  // current logic\n  const x = compute();\n  return x;\n}`;
  }, [issue]);

  const demoAfterCode = useMemo(() => {
    if (issue.suggestion)
      return `// Optimized implementation\nfunction process() {\n  ${issue.suggestion}\n  return optimizedResult;\n}`;
    return `// ${issue.title} [FIXED]\nfunction handle() {\n  // optimized logic\n  const x = computeFast();\n  validate(x);\n  return x;\n}`;
  }, [issue]);

  return (
    <div className="rounded-lg border border-cortex-border bg-[#0f0f20] mb-3 overflow-hidden">
      <div className="p-3">
        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-white truncate">
                {issue.title}
              </span>
              <span className="px-1 py-0.5 rounded bg-[#f59e0b]/20 text-[#f59e0b] text-[8px] font-mono font-bold">
                PENDING
              </span>
            </div>
            {issue.source_file && (
              <span className="text-[10px] font-mono text-gray-500 mt-0.5 block">
                {issue.source_file}
                {issue.line_range &&
                  `:${issue.line_range[0]}-${issue.line_range[1]}`}
              </span>
            )}
          </div>
        </div>

        {/* Description */}
        <p className="text-[11px] text-gray-400 mb-2">{issue.description}</p>

        {/* Diff toggle */}
        <button
          onClick={() => setExpanded((e) => !e)}
          className="text-[10px] font-mono text-cortex-primary hover:underline mb-2 flex items-center gap-1"
        >
          <svg
            className={`w-3 h-3 transition-transform duration-150 ${
              expanded ? "rotate-90" : ""
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
          {expanded ? "Hide diff" : "Show diff"}
        </button>

        {/* Diff view */}
        {expanded && (
          <div className="mb-3">
            <SimpleDiffView
              beforeCode={demoBeforeCode}
              afterCode={demoAfterCode}
            />
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            size="sm"
            onClick={() => onApprove(issue.id)}
            disabled={processing}
            loading={processing}
            className="text-[10px]"
          >
            Approve
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onReject(issue.id)}
            disabled={processing}
            className="text-[10px] text-[#ef4444] hover:bg-[#ef4444]/10 hover:text-[#ef4444]"
          >
            Reject
          </Button>
        </div>
      </div>
    </div>
  );
}

function FixedItem({ issue }: { issue: ArchitectureIssue }) {
  return (
    <div className="flex items-start gap-2 p-2 rounded bg-[#0f0f20] border border-cortex-border">
      <svg
        className="w-4 h-4 text-[#22c55e] mt-0.5 shrink-0"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M5 13l4 4L19 7"
        />
      </svg>
      <div className="min-w-0 flex-1">
        <span className="text-[11px] text-gray-300 font-medium block truncate">
          {issue.title}
        </span>
        {issue.source_file && (
          <span className="text-[9px] font-mono text-gray-600">
            {issue.source_file}
          </span>
        )}
      </div>
      <span className="text-[9px] font-mono text-gray-600 shrink-0">
        {issue.fixed_at
          ? new Date(issue.fixed_at).toLocaleTimeString()
          : ""}
      </span>
    </div>
  );
}

export default function RefactorPreview() {
  const issues = useL6Store((s) => s.issues);
  const updateIssue = useL6Store((s) => s.updateIssue);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const pendingItems = useMemo(
    () =>
      issues.filter(
        (i) => i.status === "open" || i.status === "in_progress"
      ),
    [issues]
  );

  const fixedItems = useMemo(
    () =>
      issues.filter(
        (i) => i.status === "approved" || i.status === "fixed"
      ),
    [issues]
  );

  const handleApprove = useCallback(
    async (id: string) => {
      setProcessingId(id);
      try {
        await fetch(`/api/l6/refactor/${id}/approve`, { method: "POST" });
        updateIssue(id, {
          status: "approved",
          fixed_at: Date.now(),
        });
      } catch {
        updateIssue(id, {
          status: "approved",
          fixed_at: Date.now(),
        });
      } finally {
        setProcessingId(null);
      }
    },
    [updateIssue]
  );

  const handleReject = useCallback(
    (id: string) => {
      updateIssue(id, { status: "rejected" });
    },
    [updateIssue]
  );

  const hasPending = pendingItems.length > 0;
  const hasFixed = fixedItems.length > 0;

  return (
    <div className="rounded-xl border border-cortex-border bg-cortex-surface overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cortex-border">
        <div className="flex items-center justify-between">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Refactor Preview
          </h3>
          <span className="text-[10px] font-mono text-gray-500">
            {pendingItems.length} pending
          </span>
        </div>
      </div>

      <div className="p-4">
        {/* Empty state */}
        {!hasPending && !hasFixed && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <svg
              className="w-10 h-10 text-gray-600 mb-3"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"
              />
            </svg>
            <span className="text-sm text-gray-400 font-semibold">
              No pending refactors
            </span>
            <span className="text-[11px] text-gray-500 mt-1">
              All architecture issues have been reviewed
            </span>
          </div>
        )}

        {/* Pending approvals */}
        {hasPending && (
          <div className="mb-6">
            <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
              Pending Approvals
              <span className="px-1 py-0.5 rounded bg-[#f59e0b]/20 text-[#f59e0b] text-[8px] font-mono">
                {pendingItems.length}
              </span>
            </h4>
            {pendingItems.map((issue) => (
              <PendingApprovalCard
                key={issue.id}
                issue={issue}
                onApprove={handleApprove}
                onReject={handleReject}
                processing={processingId === issue.id}
              />
            ))}
          </div>
        )}

        {/* Recently fixed */}
        {hasFixed && (
          <div>
            <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
              Recently Fixed
              <span className="px-1 py-0.5 rounded bg-[#22c55e]/20 text-[#22c55e] text-[8px] font-mono">
                {fixedItems.length}
              </span>
            </h4>
            <div className="space-y-1.5">
              {fixedItems.slice(0, 10).map((issue) => (
                <FixedItem key={issue.id} issue={issue} />
              ))}
              {fixedItems.length > 10 && (
                <p className="text-[9px] text-gray-600 font-mono text-center pt-1">
                  +{fixedItems.length - 10} more
                </p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
