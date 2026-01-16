'use client';

/**
 * LiveTaskUpdates Component - Phase 9
 *
 * React component that provides real-time task updates via WebSocket.
 * Manages WebSocket connection lifecycle and broadcasts updates to child components.
 *
 * Usage:
 * ```tsx
 * <LiveTaskUpdates onTaskUpdate={(update) => handleUpdate(update)}>
 *   <TaskList tasks={tasks} />
 * </LiveTaskUpdates>
 * ```
 */

import { useEffect, useState, useCallback, createContext, useContext, ReactNode } from 'react';
import { useSession } from '@/lib/auth-client';
import { getWebSocketManager, WebSocketMessage, TaskUpdateMessage } from '@/lib/websocket';

// Task update event types
export type TaskUpdateType =
  | 'task.created'
  | 'task.updated'
  | 'task.completed'
  | 'task.deleted';

// Simplified task update for consumers
export interface TaskUpdate {
  type: TaskUpdateType;
  taskId: string;
  taskData?: {
    id?: string;
    title?: string;
    description?: string;
    completed?: boolean;
    priority?: string;
    tags?: string[];
    due_date?: string;
    recurrence_id?: string;
  };
  timestamp: string;
}

// Connection status
export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

// Context value
interface LiveTaskUpdatesContextValue {
  status: ConnectionStatus;
  lastUpdate: TaskUpdate | null;
  isConnected: boolean;
}

const LiveTaskUpdatesContext = createContext<LiveTaskUpdatesContextValue>({
  status: 'disconnected',
  lastUpdate: null,
  isConnected: false,
});

// Hook to access live task updates context
export function useLiveTaskUpdates() {
  return useContext(LiveTaskUpdatesContext);
}

interface LiveTaskUpdatesProps {
  children: ReactNode;
  onTaskUpdate?: (update: TaskUpdate) => void;
  onConnectionChange?: (status: ConnectionStatus) => void;
  showStatusIndicator?: boolean;
}

/**
 * LiveTaskUpdates Provider Component
 *
 * Wraps children with WebSocket connection management.
 * Automatically connects when user is authenticated.
 * Handles reconnection and cleanup on unmount.
 */
export function LiveTaskUpdates({
  children,
  onTaskUpdate,
  onConnectionChange,
  showStatusIndicator = true,
}: LiveTaskUpdatesProps) {
  const { data: session } = useSession();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [lastUpdate, setLastUpdate] = useState<TaskUpdate | null>(null);

  // Handle incoming task updates
  const handleMessage = useCallback(
    (message: WebSocketMessage) => {
      // Filter for task update messages
      if (
        message.type === 'task.created' ||
        message.type === 'task.updated' ||
        message.type === 'task.completed' ||
        message.type === 'task.deleted'
      ) {
        const taskMessage = message as TaskUpdateMessage;
        const update: TaskUpdate = {
          type: taskMessage.type as TaskUpdateType,
          taskId: taskMessage.task_id,
          taskData: taskMessage.task_data,
          timestamp: taskMessage.timestamp,
        };

        setLastUpdate(update);
        onTaskUpdate?.(update);
      }
    },
    [onTaskUpdate]
  );

  // Track user ID for connection management
  const userId = session?.user?.id;

  // Manage WebSocket connection
  useEffect(() => {
    // If no user, ensure we're in disconnected state via callback in cleanup
    if (!userId) {
      // Use ref-based approach or skip - the initial state is already 'disconnected'
      return;
    }

    const wsManager = getWebSocketManager();
    let isMounted = true;

    // Set up handlers (these are async callbacks, not synchronous in effect body)
    const unsubMessage = wsManager.onMessage(handleMessage);
    const unsubConnect = wsManager.onConnect(() => {
      if (isMounted) {
        setStatus('connected');
        onConnectionChange?.('connected');
      }
    });
    const unsubDisconnect = wsManager.onDisconnect(() => {
      if (isMounted) {
        setStatus('disconnected');
        onConnectionChange?.('disconnected');
      }
    });
    const unsubError = wsManager.onError(() => {
      if (isMounted) {
        setStatus('error');
        onConnectionChange?.('error');
      }
    });

    // Connect asynchronously
    setStatus('connecting');
    onConnectionChange?.('connecting');
    wsManager.connect(userId);

    // Cleanup on unmount
    return () => {
      isMounted = false;
      unsubMessage();
      unsubConnect();
      unsubDisconnect();
      unsubError();
      wsManager.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const contextValue: LiveTaskUpdatesContextValue = {
    status,
    lastUpdate,
    isConnected: status === 'connected',
  };

  return (
    <LiveTaskUpdatesContext.Provider value={contextValue}>
      {showStatusIndicator && <ConnectionStatusIndicator status={status} />}
      {children}
    </LiveTaskUpdatesContext.Provider>
  );
}

/**
 * Connection Status Indicator
 *
 * Shows a small indicator of WebSocket connection status.
 * Hidden when connected (to avoid visual clutter).
 */
function ConnectionStatusIndicator({ status }: { status: ConnectionStatus }) {
  // Don't show anything when connected (smooth UX)
  if (status === 'connected') {
    return null;
  }

  const statusConfig = {
    connecting: {
      color: 'bg-yellow-400',
      text: 'Connecting...',
      animate: true,
    },
    disconnected: {
      color: 'bg-gray-400',
      text: 'Offline',
      animate: false,
    },
    error: {
      color: 'bg-red-400',
      text: 'Connection error',
      animate: false,
    },
  };

  const config = statusConfig[status] || statusConfig.disconnected;

  return (
    <div className="fixed bottom-4 right-4 flex items-center gap-2 bg-white dark:bg-gray-800 px-3 py-2 rounded-full shadow-lg border border-gray-200 dark:border-gray-700 text-sm z-50">
      <div
        className={`w-2 h-2 rounded-full ${config.color} ${config.animate ? 'animate-pulse' : ''}`}
      />
      <span className="text-gray-600 dark:text-gray-300">{config.text}</span>
    </div>
  );
}

/**
 * Hook to subscribe to specific task update types
 *
 * Usage:
 * ```tsx
 * useTaskUpdateSubscription('task.created', (update) => {
 *   console.log('New task created:', update);
 * });
 * ```
 */
export function useTaskUpdateSubscription(
  type: TaskUpdateType | TaskUpdateType[],
  callback: (update: TaskUpdate) => void
) {
  const { lastUpdate } = useLiveTaskUpdates();

  useEffect(() => {
    if (!lastUpdate) return;

    const types = Array.isArray(type) ? type : [type];

    if (types.includes(lastUpdate.type)) {
      callback(lastUpdate);
    }
  }, [lastUpdate, type, callback]);
}

export default LiveTaskUpdates;
