import { useState, useCallback } from 'react';
import { TaskInput } from './components/TaskInput';
import { AgentView } from './components/AgentView';
import { useAgentStream } from './hooks/useAgentStream';

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleTaskSubmit = useCallback((sid: string) => {
    setSessionId(sid);
  }, []);

  const handleNewTask = useCallback(() => {
    setSessionId(null);
  }, []);

  const stream = useAgentStream(sessionId);

  return (
    <div className="app">
      {/* Top bar */}
      <header className="app-header">
        <div className="app-logo">
          <span className="logo-icon">◈</span>
          <span className="logo-text">Manus Platform</span>
        </div>
        {sessionId && (
          <div className="app-header-right">
            <span className="session-id">Session: {sessionId.slice(0, 8)}</span>
            <button onClick={handleNewTask} className="new-task-btn">
              + New Task
            </button>
          </div>
        )}
      </header>

      {/* Main content */}
      <main className="app-main">
        {!sessionId ? (
          <div className="welcome-screen">
            <div className="welcome-hero">
              <h1 className="hero-title">Autonomous AI Agent</h1>
              <p className="hero-subtitle">
                Submit a task. Watch the agent think, plan, and execute in real-time.
              </p>
            </div>
            <TaskInput onSubmit={handleTaskSubmit} />
          </div>
        ) : (
          <div className="workspace-layout">
            {/* Left: Task input + session info */}
            <aside className="left-panel">
              <TaskInput onSubmit={handleTaskSubmit} />
            </aside>

            {/* Right: Live agent workspace */}
            <section className="right-panel">
              <AgentView state={stream} />
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
