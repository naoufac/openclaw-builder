import type { AgentStreamState } from '../types';
import { TerminalPanel } from './TerminalPanel';
import { TodoPanel } from './TodoPanel';
import { FileBrowser } from './FileBrowser';

interface AgentViewProps {
  state: AgentStreamState;
}

export function AgentView({ state }: AgentViewProps) {
  const { isComplete, error } = state;

  return (
    <div className="agent-view">
      {/* Status bar */}
      <div className={`agent-status-bar ${error ? 'error' : isComplete ? 'complete' : 'active'}`}>
        {error ? (
          <>❌ Error: {error}</>
        ) : isComplete ? (
          <>✅ Task complete</>
        ) : state.events.length > 0 ? (
          <>⚡ Agent working...</>
        ) : (
          <>⏳ Waiting for agent to start...</>
        )}
      </div>

      {/* Three-panel layout */}
      <div className="agent-panels">
        <div className="agent-panel agent-panel-todo">
          <TodoPanel state={state} />
        </div>

        <div className="agent-panel agent-panel-terminal">
          <TerminalPanel
            events={state.events}
            isComplete={isComplete}
            error={error}
          />
        </div>

        <div className="agent-panel agent-panel-files">
          <FileBrowser files={state.files} />
        </div>
      </div>
    </div>
  );
}
