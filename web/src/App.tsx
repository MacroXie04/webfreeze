import { useRef, useState } from "react";
import { UrlBar } from "./components/UrlBar";
import { PreviewFrame } from "./components/PreviewFrame";
import { ExportButton } from "./components/ExportButton";
import {
  createSession,
  freeze,
  type Mode,
  type SessionResponse,
  type FreezeReport,
} from "./api";

export default function App() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<FreezeReport | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  async function handleLoad(url: string, mode: Mode) {
    setLoading(true);
    setError(null);
    setReport(null);
    setSession(null);
    try {
      setSession(await createSession(url, mode));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleExport() {
    if (!session) return;
    setExporting(true);
    setError(null);
    try {
      // P1: whole-page export. P2 will grab the iframe DOM + data-wf-keep markers
      // (via iframeRef) and send keep="selection".
      const res = await freeze(session.sessionId, "whole", {
        inlineImages: true,
        jsFidelity: "off",
      });
      setReport(res.report);
      downloadHtml(res.html, session.title);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <span className="brand">webfreeze</span>
        <UrlBar loading={loading} onLoad={handleLoad} />
        <ExportButton disabled={!session} exporting={exporting} onExport={handleExport} />
      </header>

      {error && <div className="banner banner--error">{error}</div>}
      {session?.warnings?.map((w, i) => (
        <div className="banner banner--warn" key={i}>
          {w}
        </div>
      ))}
      {report && (
        <div className="banner banner--ok">
          Exported {report.sizeKB} KB · {report.keptScripts} script(s) kept
        </div>
      )}

      <main className="content">
        <PreviewFrame ref={iframeRef} previewUrl={session?.previewUrl ?? null} />
      </main>
    </div>
  );
}

function downloadHtml(html: string, title: string) {
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${(title || "frozen").replace(/[^\w.-]+/g, "_")}.html`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
