import { useCallback, useEffect, useRef, useState } from 'react';
import type { AgentEvent, AgentStreamState, TodoItem, FileEntry } from '../types';

const initialState: AgentStreamState = {
  events: [],
  thoughts: [],
  toolCalls: [],
  toolResults: [],
  todos: [],
  isComplete: false,
  error: null,
  files: [],
};

/**
 * Parses a todo.md text block into structured todo items.
 * Recognizes lines like:
 *   - [ ] Step description     → not done
 *   - [x] Step description     → done
 *   1. Step description         → numbered, not done
 *   1. ~~Step description~~     → numbered, done (strikethrough)
 */
function parseTodos(text: string): TodoItem[] {
  const lines = text.split('\n');
  const items: TodoItem[] = [];

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) continue;

    // Checkbox format: - [ ] or - [x]
    const checkboxMatch = trimmed.match(/^-\s+\[([ x])\]\s+(.+)$/i);
    if (checkboxMatch) {
      items.push({
        done: checkboxMatch[1].toLowerCase() === 'x',
        step: checkboxMatch[2].replace(/~~/g, '').trim(),
        raw: trimmed,
      });
      continue;
    }

    // Numbered format: "1. Step" or "1. ~~Step~~"
    const numberedMatch = trimmed.match(/^(\d+)\.\s+(.+)$/);
    if (numberedMatch) {
      const rawStep = numberedMatch[2];
      const isStruck = rawStep.includes('~~');
      items.push({
        done: isStruck,
        step: rawStep.replace(/~~/g, '').trim(),
        raw: trimmed,
      });
      continue;
    }

    // Bullet format: "- Step" or "- ~~Step~~"
    const bulletMatch = trimmed.match(/^[-*]\s+(.+)$/);
    if (bulletMatch) {
      const rawStep = bulletMatch[1];
      const isStruck = rawStep.includes('~~');
      items.push({
        done: isStruck,
        step: rawStep.replace(/~~/g, '').trim(),
        raw: trimmed,
      });
      continue;
    }
  }

  return items;
}

/**
 * WebSocket hook for real-time agent stream.
 * Connects to /ws/{sessionId} and parses incoming events.
 */
export function useAgentStream(sessionId: string | null): AgentStreamState & {
  clear: () => void;
} {
  const [state, setState] = useState<AgentStreamState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clear = useCallback(() => setState(initialState), []);

  useEffect(() => {
    if (!sessionId) {
      setState(initialState);
      return;
    }

    setState(initialState);

    let closed = false;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/${sessionId}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[ws] connected to session ${sessionId}`);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as AgentEvent;
          const typedEvent: AgentEvent = {
            ...msg,
            timestamp: msg.timestamp || Date.now(),
          };

          setState((prev) => {
            const next: AgentStreamState = {
              ...prev,
              events: [...prev.events, typedEvent],
              thoughts:
                typedEvent.type === 'thought'
                  ? [...prev.thoughts, typedEvent]
                  : prev.thoughts,
              toolCalls:
                typedEvent.type === 'tool_call'
                  ? [...prev.toolCalls, typedEvent]
                  : prev.toolCalls,
              toolResults:
                typedEvent.type === 'tool_result'
                  ? [...prev.toolResults, typedEvent]
                  : prev.toolResults,
            };

            if (typedEvent.type === 'todo_update') {
              next.todos = parseTodos(typedEvent.data);
            }

            if (typedEvent.type === 'complete') {
              next.isComplete = true;
            }

            if (typedEvent.type === 'error') {
              next.error = typedEvent.data;
            }

            if (
              typedEvent.type === 'file_created' ||
              typedEvent.type === 'file_modified'
            ) {
              const entry: FileEntry = {
                path: typedEvent.data,
                action: typedEvent.type === 'file_created' ? 'created' : 'modified',
                timestamp: typedEvent.timestamp,
              };
              // Avoid duplicates — update if path exists
              const existing = next.files.findIndex((f) => f.path === entry.path);
              if (existing >= 0) {
                next.files = [...next.files];
                next.files[existing] = entry;
              } else {
                next.files = [...next.files, entry];
              }
            }

            return next;
          });
        } catch {
          // Non-JSON or malformed — treat as raw text
          const rawEvent: AgentEvent = {
            type: 'thought',
            data: event.data,
            timestamp: Date.now(),
          };
          setState((prev) => ({
            ...prev,
            events: [...prev.events, rawEvent],
            thoughts: [...prev.thoughts, rawEvent],
          }));
        }
      };

      ws.onerror = () => {
        console.error('[ws] error');
      };

      ws.onclose = () => {
        console.log('[ws] closed');
        if (!closed && !reconnectTimer.current) {
          reconnectTimer.current = setTimeout(() => {
            reconnectTimer.current = null;
            if (!closed) connect();
          }, 3000);
        }
      };
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [sessionId]);

  return { ...state, clear };
}
