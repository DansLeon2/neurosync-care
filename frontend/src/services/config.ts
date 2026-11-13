const apiBase = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '');
const websocket = new URL(apiBase || window.location.origin, window.location.origin);
websocket.protocol = websocket.protocol === 'https:' ? 'wss:' : 'ws:';
websocket.pathname = `${websocket.pathname.replace(/\/$/, '')}/ws/stream`;
export const config = {
  apiBase,
  websocketUrl: import.meta.env.VITE_WS_URL || websocket.toString(),
  reconnectMs: 2000,
};
