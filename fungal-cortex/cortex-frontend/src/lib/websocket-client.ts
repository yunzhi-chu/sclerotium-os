/** WebSocket client with auto-reconnect and exponential backoff. */

type MessageHandler = (data: unknown) => void;

interface WSState {
  socket: WebSocket | null;
  url: string;
  handlers: Map<string, Set<MessageHandler>>;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  baseDelay: number;
  maxDelay: number;
  isConnecting: boolean;
  isClosed: boolean;
}

function createWSState(url: string): WSState {
  return {
    socket: null,
    url,
    handlers: new Map(),
    reconnectAttempts: 0,
    maxReconnectAttempts: 20,
    baseDelay: 500,
    maxDelay: 30_000,
    isConnecting: false,
    isClosed: false,
  };
}

const connections: Map<string, WSState> = new Map();

function getBackoffDelay(attempt: number, base: number, max: number): number {
  return Math.min(base * Math.pow(2, attempt) + Math.random() * 100, max);
}

function connect(state: WSState): void {
  if (state.isConnecting || state.isClosed) return;
  state.isConnecting = true;

  const socket = new WebSocket(state.url);
  state.socket = socket;

  socket.onopen = () => {
    state.reconnectAttempts = 0;
    state.isConnecting = false;
  };

  socket.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      const type = msg.type ?? "unknown";
      const handlerSet = state.handlers.get(type);
      if (handlerSet) {
        handlerSet.forEach((fn) => fn(msg));
      }
      const allHandlers = state.handlers.get("*");
      if (allHandlers) {
        allHandlers.forEach((fn) => fn(msg));
      }
    } catch {
      // Binary or non-JSON message — ignored
    }
  };

  socket.onclose = () => {
    state.isConnecting = false;
    if (!state.isClosed && state.reconnectAttempts < state.maxReconnectAttempts) {
      const delay = getBackoffDelay(
        state.reconnectAttempts,
        state.baseDelay,
        state.maxDelay
      );
      state.reconnectAttempts++;
      setTimeout(() => connect(state), delay);
    }
  };

  socket.onerror = () => {
    socket.close();
  };
}

export function subscribe(
  endpoint: string,
  messageType: string,
  handler: MessageHandler
): () => void {
  let state = connections.get(endpoint);
  if (!state) {
    state = createWSState(endpoint);
    connections.set(endpoint, state);
    connect(state);
  }

  let handlerSet = state.handlers.get(messageType);
  if (!handlerSet) {
    handlerSet = new Set();
    state.handlers.set(messageType, handlerSet);
  }
  handlerSet.add(handler);

  return () => {
    handlerSet?.delete(handler);
    if (handlerSet?.size === 0) {
      state?.handlers.delete(messageType);
    }
    // Auto-close if no handlers remain after 5s
    if (state && state.handlers.size === 0) {
      setTimeout(() => {
        if (state.handlers.size === 0 && state.socket) {
          state.isClosed = true;
          state.socket.close();
          connections.delete(endpoint);
        }
      }, 5000);
    }
  };
}

export function closeAll(): void {
  connections.forEach((state) => {
    state.isClosed = true;
    state.socket?.close();
  });
  connections.clear();
}
