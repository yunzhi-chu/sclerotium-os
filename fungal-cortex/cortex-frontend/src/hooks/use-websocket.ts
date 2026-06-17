import { useEffect, useRef, useCallback } from "react";
import { subscribe } from "@/lib/websocket-client";

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000";

export function useWebSocket(
  endpoint: string,
  messageType: string,
  handler: (data: unknown) => void,
  enabled: boolean = true
): void {
  const handlerRef = useRef(handler);
  handlerRef.current = handler;

  const stableHandler = useCallback(
    (data: unknown) => handlerRef.current(data),
    []
  );

  useEffect(() => {
    if (!enabled) return;
    const url = `${WS_BASE}/ws/${endpoint}`;
    const unsub = subscribe(url, messageType, stableHandler);
    return unsub;
  }, [endpoint, messageType, enabled, stableHandler]);
}
