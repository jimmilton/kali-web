'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
import {
  getSocket,
  disconnectSocket,
  subscribeToJob,
  unsubscribeFromJob,
  subscribeToProject,
  unsubscribeFromProject,
  onJobOutput,
  onJobStatus,
  onNotification,
  sendJobInput,
  isConnected,
  JobOutputEvent,
  JobStatusEvent,
  NotificationEvent,
} from '@/lib/socket';
import { useAuthStore } from '@/stores/auth-store';

export function useSocket() {
  const [connected, setConnected] = useState(false);
  const { isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) {
      disconnectSocket();
      setConnected(false);
      return;
    }

    const socket = getSocket();

    const handleConnect = () => setConnected(true);
    const handleDisconnect = () => setConnected(false);

    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);

    setConnected(socket.connected);

    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
    };
  }, [isAuthenticated]);

  return { connected, isConnected: connected };
}

export function useJobOutput(jobId: string | null) {
  const [outputs, setOutputs] = useState<JobOutputEvent[]>([]);
  const [status, setStatus] = useState<JobStatusEvent | null>(null);

  useEffect(() => {
    if (!jobId) return;

    subscribeToJob(jobId);

    const unsubOutput = onJobOutput((data) => {
      if (data.job_id === jobId) {
        setOutputs((prev) => [...prev, data]);
      }
    });

    const unsubStatus = onJobStatus((data) => {
      if (data.job_id === jobId) {
        setStatus(data);
      }
    });

    return () => {
      unsubscribeFromJob(jobId);
      unsubOutput();
      unsubStatus();
    };
  }, [jobId]);

  const sendInput = useCallback(
    (input: string) => {
      if (jobId) {
        sendJobInput(jobId, input);
      }
    },
    [jobId]
  );

  const clearOutputs = useCallback(() => {
    setOutputs([]);
  }, []);

  return { outputs, status, sendInput, clearOutputs };
}

export function useProjectEvents(projectId: string | null) {
  const [jobUpdates, setJobUpdates] = useState<JobStatusEvent[]>([]);

  useEffect(() => {
    if (!projectId) return;

    subscribeToProject(projectId);

    const unsubStatus = onJobStatus((data) => {
      setJobUpdates((prev) => {
        const existing = prev.findIndex((u) => u.job_id === data.job_id);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = data;
          return updated;
        }
        return [...prev, data];
      });
    });

    return () => {
      unsubscribeFromProject(projectId);
      unsubStatus();
    };
  }, [projectId]);

  const clearUpdates = useCallback(() => {
    setJobUpdates([]);
  }, []);

  return { jobUpdates, clearUpdates };
}

export function useNotifications(callback?: (notification: NotificationEvent) => void) {
  const [notifications, setNotifications] = useState<NotificationEvent[]>([]);
  const callbackRef = useRef(callback);
  callbackRef.current = callback;

  useEffect(() => {
    const unsub = onNotification((data) => {
      setNotifications((prev) => [data, ...prev].slice(0, 50));
      callbackRef.current?.(data);
    });

    return unsub;
  }, []);

  const clearNotifications = useCallback(() => {
    setNotifications([]);
  }, []);

  return { notifications, clearNotifications };
}

export function useLiveJobStatus(jobId: string | null, initialStatus?: string) {
  const [status, setStatus] = useState(initialStatus || 'pending');
  const [exitCode, setExitCode] = useState<number | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    subscribeToJob(jobId);

    const unsub = onJobStatus((data) => {
      if (data.job_id === jobId) {
        setStatus(data.status);
        if (data.exit_code !== undefined) setExitCode(data.exit_code);
        if (data.error_message) setErrorMessage(data.error_message);
      }
    });

    return () => {
      unsubscribeFromJob(jobId);
      unsub();
    };
  }, [jobId]);

  return { status, exitCode, errorMessage };
}
