import { ChatPanel } from "./components/ChatPanel";
import { UploadPanel } from "./components/UploadPanel";

export default function App() {
  return (
    <main className="container">
      <header>
        <h1>Medical Diagnostics Support</h1>
        <p className="muted">
          Upload clinical reference documents and ask questions grounded in their content. Answers
          support, not replace, professional judgement.
        </p>
      </header>
      <UploadPanel />
      <ChatPanel />
    </main>
  );
}
