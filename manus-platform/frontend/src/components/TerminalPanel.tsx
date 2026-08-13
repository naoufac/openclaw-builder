import { useEffect, useRef } from 'react';
import type { AgentEvent } from '../types';

interface TerminalPanelProps {
  events: AgentEvent[];
  isComplete: boolean;
  error: string | null;
}

function formatEvent(event: AgentEvent): { prefix: string; text: string; className: string } {
  const time = new Date(event.timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });

  switch (event.type) {
    case 'thought':
      return {
        prefix: `[${time}] 💭`,
        text: event.data,
        className: 'terminal-line terminal-thought',
      };
    case 'tool_call':
      return {
        prefix: `[${time}] 🔧`,
        text: event.tool ? `${event.tool}(${event.data})` : event.data,
        className: 'terminal-line terminal-tool-call',
      };
    case 'tool_result':
      return {
        prefix: `[${time}] 📤`,
        text: event.data,
        className: 'terminal-line terminal-tool-result',
      };
    case 'todo_update':
      return {
        prefix: `[${time}] 📋`,
        text: 'Plan updated',
        className: 'terminal-line terminal-todo',
      };
    case 'file_created':
      return {
        prefix: `[${time}] 📄+`,
        text: event.data,
        className: 'terminal-line terminal-file-created',
      };
    case 'file_modified':
      return {
        prefix: `[${time}] 📄~`,
        text: event.data,
        className: 'terminal-line terminal-file-modified',
      };
    case 'complete':
      return {
        prefix: `[${time}] ✅`,
        text: event.data || 'Task complete',
        className: 'terminal-line terminal-complete',
      };
    case 'error':
      return {
        prefix: `[${time}] ❌`,
        text: event.data,
        className: 'terminal-line terminal-error',
      };
    default:
      return {
        prefix: `[${time}]`,
        text: event.data,
        className: 'terminal-line',
      };
  }
}

export function TerminalPanel({ events, isComplete, error }: TerminalPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <div className="terminal-panel">
      <div className="panel-header">
        <h3 className="panel-title-sm">🖥 Terminal</h3>
        <div className="terminal-status">
          {error ? (
            <span className="status-dot status-error" />
          ) : isComplete ? (
            <span className="status-dot status-complete" />
          ) : events.length > 0 ? (
            <>
              <span className="status-dot status-active" />
              <span className="status-text">Running</span>
            </>
          ) : (
            <span className="status-dot status-idle" />
          )}
        </div>
      </div>

      <div className="terminal-body" ref={scrollRef}>
        {events.length === 0 && (
          <div className="terminal-line terminal-idle">
            <span className="terminal-prefix">$</span> Waiting for agent output...
          </div>
        )}
        {events.map((event, i) => {
          const { prefix, text, className } = formatEvent(event);
          return (
            <div key={i} className={className}>
              <span className="terminal-prefix">{prefix}</span>
              <span className="terminal-text">{text}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
