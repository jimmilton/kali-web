import { io, Socket } from 'socket.io-client';
import { getAccessToken } from './auth';

const SOCKET_URL = process.env.NEXT_PUBLIC_WS_URL || 'http://localhost:8000';

let socket: Socket | null = null;

export interface JobOutputEvent {
  job_id: string;
  output_type: 'stdout' | 'stderr' | 'system';
  content: string;
  timestamp: string;
}

export interface JobStatusEvent {
  job_id: string;
  status: string;
  exit_code?: number;
  error_message?: string;
}

export interface NotificationEvent {
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  project_id?: string;
  job_id?: string;
}

export type SocketEventMap = {
  job_output: JobOutputEvent;
  job_status: JobStatusEvent;
  notification: NotificationEvent;
  connect: void;
  disconnect: void;
  connect_error: Error;
};

export function getSocket(): Socket {
  if (socket && socket.connected) {
    return socket;
  }

  const token = getAccessToken();

  socket = io(SOCKET_URL, {
    auth: token ? { token } : undefined,
    transports: ['websocket', 'polling'],
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
  });

  socket.on('connect', () => {
    console.log('Socket connected:', socket?.id);
  });

  socket.on('disconnect', (reason) => {
    console.log('Socket disconnected:', reason);
  });

  socket.on('connect_error', (error) => {
    console.error('Socket connection error:', error);
  });

  return socket;
}

export function disconnectSocket(): void {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}

export function subscribeToJob(jobId: string): void {
  const s = getSocket();
  s.emit('subscribe_job', { job_id: jobId });
}

export function unsubscribeFromJob(jobId: string): void {
  const s = getSocket();
  s.emit('unsubscribe_job', { job_id: jobId });
}

export function subscribeToProject(projectId: string): void {
  const s = getSocket();
  s.emit('subscribe_project', { project_id: projectId });
}

export function unsubscribeFromProject(projectId: string): void {
  const s = getSocket();
  s.emit('unsubscribe_project', { project_id: projectId });
}

export function onJobOutput(callback: (data: JobOutputEvent) => void): () => void {
  const s = getSocket();
  s.on('job_output', callback);
  return () => s.off('job_output', callback);
}

export function onJobStatus(callback: (data: JobStatusEvent) => void): () => void {
  const s = getSocket();
  s.on('job_status', callback);
  return () => s.off('job_status', callback);
}

export function onNotification(callback: (data: NotificationEvent) => void): () => void {
  const s = getSocket();
  s.on('notification', callback);
  return () => s.off('notification', callback);
}

export function sendJobInput(jobId: string, input: string): void {
  const s = getSocket();
  s.emit('job_input', { job_id: jobId, input });
}

export function isConnected(): boolean {
  return socket?.connected ?? false;
}

export function reconnect(): void {
  if (socket && !socket.connected) {
    socket.connect();
  }
}
