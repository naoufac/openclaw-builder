import { useCallback, useEffect, useRef, useState } from 'react';
import type { AgentEvent, AgentStreamState, TodoItem, FileEntry, RawAgentEvent, EventType } from '../types';

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

    // Numbered checkbox format: "1. [✓] Step" or "1. [ ] Step"
    const numberedCheckboxMatch = trimmed.match(/^(\d+)\.\s*\[([^\]]*)\]\s*(.+)$/);
    if (numberedCheckboxMatch) {
      const marker = numberedCheckboxMatch[2].trim().toLowerCase();
      items.push({
        done: marker === 'x' || marker === '✓' || marker === '✅',
        step: numberedCheckboxMatch[3].replace(/~~/g, '').trim(),
        raw: trimmed,
      });
      continue;
    }

    // Strikethrough numbered format: "1. ~~Step~~" (treated as done)
    const struckNumberedMatch = trimmed.match(/^(\d+)\.\s+~~(.+)~~$/);
    if (struckNumberedMatch) {
      items.push({
        done: true,
        step: struckNumberedMatch[2].replace(/~~/g, '').trim(),
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
 *
 * Normalizes backend events so `data` is always a string for rendering,
 * and `timestamp` is a number. The backend sends objects for some event types;
 * we flatten/stringify them here to prevent React rendering crashes.
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
          const raw = JSON.parse(event.data) as RawAgentEvent;

          // Normalize timestamp to number (backend sends ISO string)
          const ts = raw.timestamp
            ? typeof raw.timestamp === 'string'
              ? new Date(raw.timestamp).getTime() || Date.now()
              : Number(raw.timestamp) || Date.now()
            : Date.now();

          // Normalize data payload depending on event type and backend shape
          const rawType = raw.type as string;
          const eventType = rawType as EventType;
          let dataStr = '';
          let toolName: string | undefined;
          let filePath: string | undefined;
          let fileAction: 'created' | 'modified' | undefined;
          let errorStr: string | null = null;

          const backendData = raw.data as any;

          if (rawType === 'connected') {
            dataStr = typeof backendData === 'string'
              ? backendData
              : `Connected to session ${backendData?.session_id ?? sessionId}`;
          } else if (typeof backendData === 'string') {
            dataStr = backendData;
          } else if (backendData && typeof backendData === 'object') {
            // Tool result
            if ('tool' in backendData) {
              toolName = String(backendData.tool ?? '');
            }
            if ('output' in backendData) {
              dataStr = String(backendData.output ?? '');
            } else if ('content' in backendData) {
              dataStr = String(backendData.content ?? '');
            } else if ('error' in backendData) {
              dataStr = String(backendData.error ?? '');
              errorStr = dataStr;
            } else if ('todo' in backendData) {
              dataStr = String(backendData.todo ?? '');
            } else if ('summary' in backendData) {
              dataStr = String(backendData.summary ?? '');
            } else if ('command' in backendData && 'tool' in backendData) {
              // tool_call with args
              dataStr = JSON.stringify({
                command: backendData.command,
                args: backendData.args,
              });
            } else if ('path' in backendData && 'action' in backendData) {
              // file event
              filePath = String(backendData.path ?? '');
              fileAction = backendData.action === 'modified' ? 'modified' : 'created';
              dataStr = `${fileAction} ${filePath}`;
            } else {
              dataStr = JSON.stringify(backendData);
            }
          }

          // file events may be sent under separate types, but if the backend
          // embeds them as tool_result/output text, we still need to scan
          if (!filePath && dataStr) {
            const fileWrittenMatch = dataStr.match(/(?:Wrote\s+\d+\s+bytes\s+to\s+|File\s+written\s+to\s+)`?([^`\s]+)`?/i);
            if (fileWrittenMatch) {
              filePath = fileWrittenMatch[1];
              fileAction = 'created';
            }
          }

          const typedEvent: AgentEvent = {
            type: rawType === 'connected' ? 'thought' : eventType,
            data: dataStr,
            timestamp: ts,
            tool: toolName,
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

            if (typedEvent.type === 'error' || errorStr) {
              next.error = errorStr || typedEvent.data;
            }

            if (filePath && fileAction) {
              const entries: FileEntry[] = [{
                path: filePath,
                action: fileAction,
                timestamp: ts,
              }];
              if (!filePath.includes('todo.md') && typedEvent.data.toLowerCase().includes('todo.md')) {
                entries.push({
                  path: 'todo.md',
                  action: 'created',
                  timestamp: ts,
                });
              }
              for (const entry of entries) {
                const existing = next.files.findIndex((f) => f.path === entry.path);
                if (existing >= 0) {
                  next.files = [...next.files];
                  next.files[existing] = entry;
                } else {
                  next.files = [...next.files, entry];
                }
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
