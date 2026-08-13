import { useState, useCallback } from 'react';
import type { TaskResponse } from '../types';

interface TaskInputProps {
  onSubmit: (sessionId: string, goal: string) => void;
}

export function TaskInput({ onSubmit }: TaskInputProps) {
  const [goal, setGoal] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const trimmed = goal.trim();
      if (!trimmed || loading) return;

      setLoading(true);
      setError(null);

      try {
        const res = await fetch('/api/task', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ goal: trimmed }),
        });

        if (!res.ok) {
          const text = await res.text();
          throw new Error(`Server error ${res.status}: ${text}`);
        }

        const data: TaskResponse = await res.json();
        onSubmit(data.session_id, trimmed);
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        setError(msg);
      } finally {
        setLoading(false);
      }
    },
    [goal, loading, onSubmit],
  );

  return (
    <div className="task-input-container">
      <div className="task-input-header">
        <h2 className="panel-title">New Task</h2>
        <p className="task-input-subtitle">
          Describe what you want the agent to accomplish.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="task-input-form">
        <textarea
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. Build a Python script that scrapes headlines from Hacker News and saves them to a JSON file..."
          disabled={loading}
          rows={6}
          className="task-textarea"
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
              handleSubmit(e);
            }
          }}
        />

        {error && <div className="task-error">{error}</div>}

        <button
          type="submit"
          disabled={loading || !goal.trim()}
          className="task-submit-btn"
        >
          {loading ? (
            <>
              <span className="spinner" />
              Starting agent...
            </>
          ) : (
            '▶ Launch Agent'
          )}
        </button>

        <kbd className="task-shortcut">⌘/Ctrl + Enter</kbd>
      </form>
    </div>
  );
}
