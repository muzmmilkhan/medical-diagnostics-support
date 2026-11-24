import { type FormEvent, useState } from "react";

import { askQuestion } from "../api/client";
import type { ChatMessage, Source } from "../api/types";

interface Turn extends ChatMessage {
  sources?: Source[];
}

export function ChatPanel() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed) return;

    const history: ChatMessage[] = turns.map(({ role, content }) => ({ role, content }));
    setTurns((prev) => [...prev, { role: "user", content: trimmed }]);
    setQuestion("");
    setBusy(true);
    setError(null);
    try {
      const result = await askQuestion(trimmed, history.slice(-10));
      setTurns((prev) => [
        ...prev,
        { role: "assistant", content: result.answer, sources: result.sources },
      ]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <div className="card-header">
        <h2>Ask questions</h2>
        {turns.length > 0 && (
          <button type="button" className="secondary" onClick={() => setTurns([])}>
            Clear
          </button>
        )}
      </div>

      <div className="conversation" aria-live="polite">
        {turns.length === 0 && <p className="muted">Ask about the documents you've uploaded.</p>}
        {turns.map((turn, i) => (
          <div key={i} className={`message message-${turn.role}`}>
            <p>{turn.content}</p>
            {turn.sources && turn.sources.length > 0 && (
              <details>
                <summary>Sources ({turn.sources.length})</summary>
                <ol>
                  {turn.sources.map((source, j) => (
                    <li key={j}>
                      <strong>
                        {source.source}
                        {source.page != null && `, p. ${source.page}`}
                      </strong>
                      <span className="snippet">{source.snippet}</span>
                    </li>
                  ))}
                </ol>
              </details>
            )}
          </div>
        ))}
        {busy && <p className="muted">Thinking…</p>}
      </div>

      {error && <p className="status status-error">{error}</p>}

      <form onSubmit={handleSubmit} className="question-form">
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              e.currentTarget.form?.requestSubmit();
            }
          }}
          placeholder="Enter your question…"
          aria-label="Question"
          rows={3}
        />
        <button type="submit" disabled={busy || !question.trim()}>
          Ask
        </button>
      </form>
    </section>
  );
}
