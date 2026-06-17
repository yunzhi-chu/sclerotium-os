"use client";

import { useState, useCallback } from "react";
import { useL6Store } from "@/stores/l6-store";
import type { CreateAbilityStatus } from "@/types/l6";
import { Button } from "@/components/ui/button";

interface FormState {
  gap_type: "skill" | "strategy" | "indicator";
  description: string;
  domain: string;
  requirements: string;
}

const INITIAL_FORM: FormState = {
  gap_type: "skill",
  description: "",
  domain: "",
  requirements: "",
};

const GAP_TYPE_OPTIONS = [
  { value: "skill", label: "Skill" },
  { value: "strategy", label: "Strategy" },
  { value: "indicator", label: "Indicator" },
];

const CREATE_STAGES: { key: CreateAbilityStatus["status"]; label: string }[] = [
  { key: "initiated", label: "Initiated" },
  { key: "analyzing", label: "Analyzing" },
  { key: "generating", label: "Generating" },
  { key: "validating", label: "Validating" },
  { key: "sandboxing", label: "Sandboxing" },
  { key: "completed", label: "Completed" },
];

const STAGE_ORDER: Record<CreateAbilityStatus["status"], number> = {
  initiated: 0,
  analyzing: 1,
  generating: 2,
  validating: 3,
  sandboxing: 4,
  completed: 5,
  failed: -1,
};

interface ProgressStepperProps {
  status: CreateAbilityStatus;
}

function ProgressStepper({ status }: ProgressStepperProps) {
  const currentIdx = STAGE_ORDER[status.status] ?? -1;
  const isFailed = status.status === "failed";
  const progressPct = isFailed ? 100 : Math.min(100, Math.max(0, status.progress));

  return (
    <div className="mt-4">
      {/* Progress bar */}
      <div className="h-2 rounded-full bg-[#1a1a35] overflow-hidden mb-3">
        <div
          className={[
            "h-full rounded-full transition-all duration-500 ease-out",
            isFailed ? "bg-[#ef4444]" : "bg-cortex-primary",
          ].join(" ")}
          style={{ width: `${progressPct}%` }}
        />
      </div>

      {/* Stage labels */}
      <div className="flex items-center justify-between">
        {CREATE_STAGES.map((stage, i) => {
          const isActive = i === currentIdx;
          const isCompleted = i < currentIdx;
          const isPending = i > currentIdx;

          let dotColor = "bg-[#2a2a4a]";
          if (isCompleted) dotColor = "bg-cortex-primary";
          if (isActive) {
            dotColor = isFailed ? "bg-[#ef4444]" : "bg-cortex-primary";
          }

          let textColor = "text-gray-600";
          if (isCompleted) textColor = "text-cortex-primary";
          if (isActive) textColor = isFailed ? "text-[#ef4444]" : "text-white";
          if (isPending) textColor = "text-gray-600";

          return (
            <div key={stage.key} className="flex flex-col items-center">
              {/* Connecting line */}
              {i > 0 && (
                <div
                  className={[
                    "absolute h-px w-[calc(100%+16px)] top-1/2 -translate-y-1/2",
                    "translate-x-[-50%] left-0 z-0",
                    isCompleted || (isActive && !isFailed)
                      ? "bg-cortex-primary/40"
                      : "bg-[#1e1e3a]",
                  ].join(" ")}
                  style={{
                    marginTop: "-8px",
                    marginLeft: "calc(-50% + 8px)",
                    width: "calc(100% - 16px)",
                  }}
                />
              )}

              {/* Dot */}
              <div
                className={[
                  "relative z-10 w-3 h-3 rounded-full border-2 transition-all duration-300",
                  dotColor,
                  isActive ? "scale-125 shadow-[0_0_8px_rgba(0,212,170,0.4)]" : "",
                  isActive && isFailed
                    ? "shadow-[0_0_8px_rgba(239,68,68,0.4)] border-[#ef4444]"
                    : "",
                  isCompleted ? "border-cortex-primary" : "border-[#2a2a4a]",
                ].join(" ")}
              />

              {/* Label */}
              <span
                className={[
                  "text-[8px] font-mono mt-1 whitespace-nowrap transition-colors duration-300",
                  textColor,
                ].join(" ")}
              >
                {stage.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Status message */}
      <div className="mt-3 text-center">
        {isFailed ? (
          <span className="text-[10px] font-mono text-[#ef4444]">
            Failed: {status.stage}
          </span>
        ) : (
          <span className="text-[10px] font-mono text-gray-400">
            {status.stage} ({progressPct.toFixed(0)}%)
          </span>
        )}
      </div>
    </div>
  );
}

interface RecentCreation {
  id: string;
  gap_type: string;
  description: string;
  created_at: number;
  result?: string;
}

function RecentCreationsList({ items }: { items: RecentCreation[] }) {
  if (items.length === 0) {
    return (
      <div className="text-center py-6">
        <span className="text-[11px] text-gray-500">No recent creations</span>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {items.map((item) => (
        <div
          key={item.id}
          className="flex items-start gap-2 p-2 rounded bg-[#0f0f20] border border-cortex-border"
        >
          <span className="px-1 py-0.5 rounded bg-[#00d4aa]/15 text-[#00d4aa] text-[8px] font-mono font-bold uppercase shrink-0 mt-0.5">
            {item.gap_type}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[11px] text-gray-300 truncate">{item.description}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[9px] font-mono text-gray-500">
                {new Date(item.created_at).toLocaleTimeString()}
              </span>
              {item.result && (
                <span className="text-[9px] font-mono text-green-400">
                  {item.result}
                </span>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function AbilityCreator() {
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [recentCreations, setRecentCreations] = useState<RecentCreation[]>([]);
  const [submitting, setSubmitting] = useState(false);

  const createStatus = useL6Store((s) => s.createStatus);
  const setCreateStatus = useL6Store((s) => s.setCreateStatus);

  const updateField = useCallback(
    <K extends keyof FormState>(field: K, value: FormState[K]) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    []
  );

  const handleCreate = useCallback(async () => {
    if (!form.description.trim()) return;

    setSubmitting(true);
    setCreateStatus({
      status: "initiated",
      progress: 0,
      stage: "Initiating ability creation...",
    });

    try {
      const body = {
        gap_type: form.gap_type,
        description: form.description,
        domain: form.domain || undefined,
        requirements: form.requirements
          ? form.requirements.split("\n").filter(Boolean)
          : undefined,
      };

      const res = await fetch("/api/l6/create-ability", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }

      const data = await res.json();

      // Simulate progress stages
      setCreateStatus({
        status: "analyzing",
        progress: 20,
        stage: "Analyzing gap requirements...",
      });

      await new Promise((r) => setTimeout(r, 600));
      setCreateStatus({
        status: "generating",
        progress: 40,
        stage: "Generating ability implementation...",
      });

      await new Promise((r) => setTimeout(r, 600));
      setCreateStatus({
        status: "validating",
        progress: 60,
        stage: "Validating against architecture...",
      });

      await new Promise((r) => setTimeout(r, 600));
      setCreateStatus({
        status: "sandboxing",
        progress: 80,
        stage: "Sandbox testing in isolation...",
      });

      await new Promise((r) => setTimeout(r, 800));
      setCreateStatus({
        status: "completed",
        progress: 100,
        stage: "Ability created and deployed.",
        result: data,
      });

      // Add to recent
      setRecentCreations((prev) => [
        {
          id: data.id ?? crypto.randomUUID(),
          gap_type: form.gap_type,
          description: form.description,
          created_at: Date.now(),
          result: "Deployed",
        },
        ...prev.slice(0, 9),
      ]);

      setForm(INITIAL_FORM);
    } catch (err) {
      setCreateStatus({
        status: "failed",
        progress: 0,
        stage: err instanceof Error ? err.message : "Creation failed",
      });
    } finally {
      setSubmitting(false);
    }
  }, [form, setCreateStatus]);

  const isFormValid = form.description.trim().length > 0;

  return (
    <div className="rounded-xl border border-cortex-border bg-cortex-surface overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cortex-border">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          M2 Ability Creation
        </h3>
      </div>

      {/* Form */}
      <div className="p-4">
        <div className="space-y-3">
          {/* Gap Type Dropdown */}
          <div>
            <label className="block text-[10px] text-gray-500 font-mono mb-1 uppercase tracking-wider">
              Gap Type
            </label>
            <select
              value={form.gap_type}
              onChange={(e) =>
                updateField("gap_type", e.target.value as FormState["gap_type"])
              }
              className="w-full rounded-lg border border-cortex-border bg-[#0f0f20] text-gray-200 text-xs font-mono px-3 py-2 focus:outline-none focus:ring-1 focus:ring-cortex-primary/50"
            >
              {GAP_TYPE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Description Textarea */}
          <div>
            <label className="block text-[10px] text-gray-500 font-mono mb-1 uppercase tracking-wider">
              Description
            </label>
            <textarea
              value={form.description}
              onChange={(e) => updateField("description", e.target.value)}
              placeholder="Describe the ability to create..."
              rows={3}
              className="w-full rounded-lg border border-cortex-border bg-[#0f0f20] text-gray-200 text-xs font-mono px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-cortex-primary/50 placeholder:text-gray-600"
            />
          </div>

          {/* Domain Input */}
          <div>
            <label className="block text-[10px] text-gray-500 font-mono mb-1 uppercase tracking-wider">
              Domain <span className="text-gray-700 normal-case">(optional)</span>
            </label>
            <input
              type="text"
              value={form.domain}
              onChange={(e) => updateField("domain", e.target.value)}
              placeholder="e.g., technical_analysis, sentiment, risk"
              className="w-full rounded-lg border border-cortex-border bg-[#0f0f20] text-gray-200 text-xs font-mono px-3 py-2 focus:outline-none focus:ring-1 focus:ring-cortex-primary/50 placeholder:text-gray-600"
            />
          </div>

          {/* Requirements Input */}
          <div>
            <label className="block text-[10px] text-gray-500 font-mono mb-1 uppercase tracking-wider">
              Requirements <span className="text-gray-700 normal-case">(optional, one per line)</span>
            </label>
            <textarea
              value={form.requirements}
              onChange={(e) => updateField("requirements", e.target.value)}
              placeholder="One requirement per line..."
              rows={2}
              className="w-full rounded-lg border border-cortex-border bg-[#0f0f20] text-gray-200 text-xs font-mono px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-cortex-primary/50 placeholder:text-gray-600"
            />
          </div>

          {/* Create Button */}
          <Button
            variant="primary"
            size="md"
            className="w-full"
            onClick={handleCreate}
            disabled={!isFormValid || submitting}
            loading={submitting}
          >
            {submitting ? "Creating..." : "Create Ability"}
          </Button>
        </div>

        {/* Progress Stepper */}
        {createStatus && <ProgressStepper status={createStatus} />}

        {/* Reset status button on failed */}
        {createStatus?.status === "failed" && (
          <div className="mt-2 text-center">
            <button
              onClick={() => setCreateStatus(null)}
              className="text-[10px] text-gray-500 hover:text-gray-300 font-mono underline"
            >
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Recent Creations */}
      <div className="border-t border-cortex-border px-4 py-3">
        <h4 className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">
          Recent Creations
        </h4>
        <RecentCreationsList items={recentCreations} />
      </div>
    </div>
  );
}
