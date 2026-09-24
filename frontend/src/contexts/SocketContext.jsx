import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from './AuthContext';

const SocketContext = createContext(null);

export function SocketProvider({ children }) {
  const { token, isAuthenticated } = useAuth();
  const [lastEvent, setLastEvent] = useState(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const listenersRef = useRef(new Map());

  const connect = useCallback(() => {
    if (!token || wsRef.current?.readyState === WebSocket.OPEN) return;

    let wsUrl;
    const rawApi = import.meta.env.VITE_API_URL;
    if (rawApi) {
      try {
        const parsed = new URL(rawApi);
        const wsProtocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${wsProtocol}//${parsed.host}/ws?token=${token}`;
      } catch {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}/ws?token=${token}`;
      }
    } else {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.host;
      wsUrl = `${protocol}//${host}/ws?token=${token}`;
    }
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      setConnected(true);
      console.log('[WS] Connected');
    };

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        const { event: eventName, data } = parsed;
        setLastEvent({ event: eventName, data, timestamp: Date.now() });

        // Notify all registered listeners for this event
        const handlers = listenersRef.current.get(eventName) || [];
        handlers.forEach(handler => handler(data));
      } catch (e) {
        console.error('[WS] Parse error:', e);
      }
    };

    ws.onclose = (e) => {
      setConnected(false);
      console.log('[WS] Disconnected, code:', e.code);

      // Auto-reconnect after 3 seconds (unless intentionally closed)
      if (e.code !== 4001 && isAuthenticated) {
        reconnectTimeoutRef.current = setTimeout(connect, 3000);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    wsRef.current = ws;
  }, [token, isAuthenticated]);

  // Connect when authenticated
  useEffect(() => {
    if (isAuthenticated && token) {
      connect();
    }
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [isAuthenticated, token, connect]);

  // Register event listener
  const on = useCallback((event, handler) => {
    if (!listenersRef.current.has(event)) {
      listenersRef.current.set(event, []);
    }
    listenersRef.current.get(event).push(handler);

    // Return unsubscribe function
    return () => {
      const handlers = listenersRef.current.get(event) || [];
      listenersRef.current.set(event, handlers.filter(h => h !== handler));
    };
  }, []);

  const value = {
    connected,
    lastEvent,
    on,
  };

  return (
    <SocketContext.Provider value={value}>
      {children}
    </SocketContext.Provider>
  );
}

export function useSocket() {
  const context = useContext(SocketContext);
  if (!context) {
    throw new Error('useSocket must be used within a SocketProvider');
  }
  return context;
}

export default SocketContext;
