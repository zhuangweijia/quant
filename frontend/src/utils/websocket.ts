import { storage } from "./storage";

type MessageHandler = (data: any) => void;

class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string = "";
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 3;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;

  connect() {
    const token = storage.getToken();
    if (!token) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    this.url = `${protocol}//${host}/ws?token=${token}`;

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.action === "pong") return;

        const msgType = msg.type;
        if (msgType) {
          const handlers = this.handlers.get(msgType) || [];
          handlers.forEach((h) => h(msg.data));
          const allHandlers = this.handlers.get("*") || [];
          allHandlers.forEach((h) => h(msg));
        }
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = (event) => {
      this.stopHeartbeat();
      if (event.code === 4001 || event.code === 1008) {
        this.reconnectAttempts = this.maxReconnectAttempts;
        return;
      }
      this.scheduleReconnect();
    };

    this.ws.onerror = () => {
      try { this.ws?.close(); } catch { /* ignore */ }
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.stopHeartbeat();
    this.reconnectAttempts = this.maxReconnectAttempts;
    this.ws?.close();
    this.ws = null;
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler?: MessageHandler) {
    if (!handler) {
      this.handlers.delete(type);
    } else {
      const handlers = this.handlers.get(type) || [];
      this.handlers.set(
        type,
        handlers.filter((h) => h !== handler)
      );
    }
  }

  send(data: object) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      this.send({ action: "ping" });
    }, 30000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
    this.reconnectAttempts++;
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }
}

export const wsClient = new WebSocketClient();
