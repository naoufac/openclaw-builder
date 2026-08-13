import type { AgentStreamState } from '../types';

interface TodoPanelProps {
  state: AgentStreamState;
}

export function TodoPanel({ state }: TodoPanelProps) {
  const { todos } = state;

  const doneCount = todos.filter((t) => t.done).length;
  const totalCount = todos.length;
  const progress = totalCount > 0 ? Math.round((doneCount / totalCount) * 100) : 0;

  // Find the first not-done item = current step
  const currentStepIndex = todos.findIndex((t) => !t.done);

  return (
    <div className="todo-panel">
      <div className="panel-header">
        <h3 className="panel-title-sm">📋 Plan</h3>
        {totalCount > 0 && (
          <span className="todo-progress-badge">
            {doneCount}/{totalCount}
          </span>
        )}
      </div>

      {totalCount > 0 && (
        <div className="todo-progress-bar">
          <div className="todo-progress-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      <div className="todo-list">
        {todos.length === 0 && (
          <p className="todo-empty">Waiting for agent to create a plan...</p>
        )}
        {todos.map((item, i) => {
          const isCurrent = i === currentStepIndex && !item.done;
          return (
            <div
              key={i}
              className={`todo-item ${item.done ? 'done' : ''} ${isCurrent ? 'current' : ''}`}
            >
              <span className="todo-marker">
                {item.done ? '✓' : isCurrent ? '▸' : '○'}
              </span>
              <span className="todo-text">{item.step}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
