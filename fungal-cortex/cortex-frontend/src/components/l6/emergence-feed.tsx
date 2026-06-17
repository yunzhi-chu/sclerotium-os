"use client";

import { useEffect, useRef, useMemo, useState } from "react";
import { useL6Store } from "@/stores/l6-store";
import type { EmergenceEvent } from "@/types/l6";

const EVENT_ICONS: Record<EmergenceEvent["event_type"], string> = {
  independent_discovery: "✨",
  collaboration: "🤝",
  crystallization: "💎",
};

const EVENT_COLORS: Record<EmergenceEvent["event_type"], string> = {
  independent_discovery: "#00d4aa",
  collaboration: "#3b82f6",
  crystallization: "#ec4899",
};

const EVENT_LABELS: Record<EmergenceEvent["event_type"], string> = {
  independent_discovery: "Independent Discovery",
  collaboration: "Collaboration",
  crystallization: "Crystallization",
};

function relativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp;
  const seconds = Math.floor(diff / 1000);
  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

interface EventCardProps {
  event: EmergenceEvent;
  index: number;
}

function EventCard({ event, index }: EventCardProps) {
  const color = EVENT_COLORS[event.event_type];
  const icon = EVENT_ICONS[event.event_type];
  const label = EVENT_LABELS[event.event_type];

  return (
    <div
      className={[
        "rounded-lg border border-cortex-border bg-[#0f0f20] p-3",
        "emergence-enter",
      ].join(" ")}
      style={{
        animationDelay: `${index * 50}ms`,
        borderLeftColor: color,
        borderLeftWidth: "3px",
      }}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <span className="text-lg leading-none mt-0.5 shrink-0">{icon}</span>

        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2 mb-1">
            <span
              className="text-[10px] font-semibold font-mono"
              style={{ color }}
            >
              {label}
            </span>
            <span className="text-[9px] font-mono text-gray-600 ml-auto shrink-0">
              {relativeTime(event.timestamp)}
            </span>
          </div>

          {/* Description */}
          <p className="text-[12px] text-gray-300 leading-relaxed mb-2">
            {event.description}
          </p>

          {/* Agents involved */}
          {event.agents_involved.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2">
              {event.agents_involved.map((agent) => (
                <span
                  key={agent}
                  className="px-1.5 py-0.5 rounded-full bg-[#1e1e3a] text-[9px] font-mono text-gray-400"
                >
                  {agent}
                </span>
              ))}
            </div>
          )}

          {/* Confidence bar */}
          {event.confidence !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-[9px] font-mono text-gray-500 shrink-0">
                Confidence
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-[#1a1a35] overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${event.confidence * 100}%`,
                    backgroundColor: color,
                  }}
                />
              </div>
              <span className="text-[9px] font-mono text-gray-400 w-8 text-right">
                {(event.confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}

          {/* Pattern name */}
          {event.pattern_name && (
            <div className="mt-1">
              <span className="text-[10px] font-mono text-gray-500">
                Pattern:{" "}
                <span className="text-cortex-primary">{event.pattern_name}</span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function EmergenceFeed() {
  const emergenceEvents = useL6Store((s) => s.emergenceEvents);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  // Auto-scroll to newest (top)
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [emergenceEvents.length, autoScroll]);

  const handleScroll = useMemo(
    () => () => {
      if (!scrollRef.current) return;
      // If scrolled down more than 100px from top, disable auto-scroll
      const isAtTop = scrollRef.current.scrollTop < 100;
      if (isAtTop !== autoScroll) {
        setAutoScroll(isAtTop);
      }
    },
    [autoScroll]
  );

  const isEmpty = emergenceEvents.length === 0;

  return (
    <div className="rounded-xl border border-cortex-border bg-cortex-surface overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-cortex-border flex items-center justify-between">
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Emergence Feed
        </h3>
        <div className="flex items-center gap-2">
          {!autoScroll && (
            <button
              onClick={() => {
                setAutoScroll(true);
                scrollRef.current?.scrollTo({ top: 0, behavior: "smooth" });
              }}
              className="text-[9px] font-mono text-cortex-primary hover:underline"
            >
              Scroll to top
            </button>
          )}
          <span className="text-[10px] font-mono text-gray-500">
            {emergenceEvents.length} events
          </span>
        </div>
      </div>

      {/* Feed */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="overflow-y-auto"
        style={{ maxHeight: "420px" }}
      >
        {/* Empty state */}
        {isEmpty && (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <span className="text-3xl mb-3 opacity-50">🔮</span>
            <span className="text-sm text-gray-400 font-semibold">
              Waiting for emergence events...
            </span>
            <span className="text-[11px] text-gray-500 mt-1 max-w-[240px]">
              Autonomous agent discoveries and collaborations will appear here
              in real-time
            </span>
          </div>
        )}

        {/* Event list */}
        {!isEmpty && (
          <div className="p-3 space-y-2">
            {emergenceEvents.map((event, idx) => (
              <EventCard key={event.id} event={event} index={idx} />
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes slideFromTop {
          from {
            opacity: 0;
            transform: translateY(-16px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        :global(.emergence-enter) {
          animation: slideFromTop 0.35s ease-out both;
        }
      `}</style>
    </div>
  );
}
