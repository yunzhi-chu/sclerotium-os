import { useWebSocket } from "./use-websocket";
import { useAgentStore } from "@/stores/agent-store";
import type { AgentNetwork } from "@/types/agent";

export function useAgentNetwork(enabled: boolean = true): void {
  const setNetwork = useAgentStore((s) => s.setNetwork);

  useWebSocket(
    "agents",
    "agent_network",
    (data) => {
      setNetwork(data as AgentNetwork);
    },
    enabled
  );
}
