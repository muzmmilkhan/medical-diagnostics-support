import { type FormEvent, useState } from "react";

import { uploadDocument } from "../api/client";

interface Status {
  kind: "info" | "success" | "error";
  text: string;
}

export function UploadPanel() {
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [statuses, setStatuses] = useState<Status[]>([]);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (files.length === 0) return;
    setBusy(true);
    setStatuses([]);
    for (const file of files) {
      try {
        const result = await uploadDocument(file);
        setStatuses((prev) => [
          ...prev,
          { kind: "success", text: `${result.filename}: ${result.chunks_processed} chunks indexed` },
        ]);
      } catch (error) {
        setStatuses((prev) => [
          ...prev,
          { kind: "error", text: `${file.name}: ${(error as Error).message}` },
        ]);
      }
    }
    setBusy(false);
  }

  return (
    <section className="card">
      <h2>Upload documents</h2>
      <form onSubmit={handleSubmit} className="upload-form">
        <input
          type="file"
          accept=".pdf,.txt"
          multiple
          aria-label="Documents to upload"
          onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
        />
        <button type="submit" disabled={busy || files.length === 0}>
          {busy ? "Uploading…" : "Upload"}
        </button>
      </form>
      <ul className="statuses" aria-live="polite">
        {statuses.map((status, i) => (
          <li key={i} className={`status status-${status.kind}`}>
            {status.text}
          </li>
        ))}
      </ul>
    </section>
  );
}
