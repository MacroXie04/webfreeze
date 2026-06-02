import { useEffect, useRef, useState } from "react";
import { UrlBar } from "./components/UrlBar";
import { PreviewFrame } from "./components/PreviewFrame";
import { PickerToolbar } from "./components/PickerToolbar";
import { OptionsPanel, type JsFidelity } from "./components/OptionsPanel";
import { JsFidelityReport } from "./components/JsFidelityReport";
import { ExportButton } from "./components/ExportButton";
import {
  createSession,
  freeze,
  type Mode,
  type SessionResponse,
  type FreezeReport,
} from "./api";

interface Selection {
  count: number;
  breadcrumb: string;
}

export default function App() {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [report, setReport] = useState<FreezeReport | null>(null);
  const [pickMode, setPickMode] = useState(false);
  const [selection, setSelection] = useState<Selection>({ count: 0, breadcrumb: "" });
  const [jsFidelity, setJsFidelity] = useState<JsFidelity>("off");

  const iframeRef = useRef<HTMLIFrameElement>(null);
  const pendingDom = useRef<((html: string) => void) | null>(null);

  // Listen for messages from the picker bootstrap running inside the iframe.
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      const d = e.data;
      if (!d || typeof d !== "object") return;
      if (d.type === "wf-selection") {
        setSelection({ count: d.count ?? 0, breadcrumb: d.current?.breadcrumb ?? "" });
      } else if (d.type === "wf-dom" && pendingDom.current) {
        pendingDom.current(d.html);
        pendingDom.current = null;
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  function postToFrame(type: string, extra?: Record<string, unknown>) {
    iframeRef.current?.contentWindow?.postMessage({ type, ...extra }, "*");
  }

  function togglePick() {
    const next = !pickMode;
    setPickMode(next);
    postToFrame("wf-pickmode", { on: next });
  }

  function grabDom(): Promise<string> {
    return new Promise((resolve, reject) => {
      const win = iframeRef.current?.contentWindow;
      if (!win) return reject(new Error("Preview not ready"));
      pendingDom.current = resolve;
      postToFrame("wf-grab-dom");
      window.setTimeout(() => {
        if (pendingDom.current) {
          pendingDom.current = null;
          reject(new Error("Timed out grabbing the page DOM"));
        }
      }, 5000);
    });
  }

  async function handleLoad(url: string, mode: Mode) {
    setLoading(true);
    setError(null);
    setReport(null);
    setSession(null);
    setPickMode(false);
    setSelection({ count: 0, breadcrumb: "" });
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
      let res;
      if (selection.count > 0) {
        const domHtml = await grabDom();
        res = await freeze(
          session.sessionId,
          "selection",
          { inlineImages: true, jsFidelity, stripUnselectedSiblings: true },
          domHtml,
        );
      } else {
        res = await freeze(session.sessionId, "whole", {
          inlineImages: true,
          jsFidelity,
        });
      }
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

      <div className="subbar">
        <PickerToolbar
          active={!!session}
          pickMode={pickMode}
          count={selection.count}
          breadcrumb={selection.breadcrumb}
          onTogglePick={togglePick}
          onParent={() => postToFrame("wf-select-parent")}
          onChild={() => postToFrame("wf-select-child")}
          onClear={() => postToFrame("wf-clear")}
        />
        <OptionsPanel jsFidelity={jsFidelity} disabled={!session} onChange={setJsFidelity} />
        <span className="hint">
          {selection.count > 0 ? "Export = selected parts only" : "Export = whole page"}
        </span>
      </div>

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
      <JsFidelityReport report={report} />

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
