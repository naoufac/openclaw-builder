// Shared types for agent stream events

export type EventType =
  | 'thought'
  | 'todo_update'
  | 'tool_call'
  | 'tool_result'
  | 'complete'
  | 'error'
  | 'file_created'
  | 'file_modified';

export interface AgentEvent {
  type: EventType;
  data: string;
  timestamp: number;
  tool?: string;
}

/**
 * Raw event as received from the backend WebSocket.
 * The backend sends objects for some event types; the hook normalizes these
 * to AgentEvent (data is always a string) before rendering.
 */
export interface RawAgentEvent {
  type: EventType;
  data: string | Record<string, any>;
  timestamp: number | string;
  tool?: string;
}

export interface AgentStreamState {
  events: AgentEvent[];
  thoughts: AgentEvent[];
  toolCalls: AgentEvent[];
  toolResults: AgentEvent[];
  todos: TodoItem[];
  isComplete: boolean;
  error: string | null;
  files: FileEntry[];
}

export interface TodoItem {
  step: string;
  done: boolean;
  raw: string;
}

export interface FileEntry {
  path: string;
  action: 'created' | 'modified';
  timestamp: number;
}

export interface TaskResponse {
  session_id: string;
  status: string;
}
