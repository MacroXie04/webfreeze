import { useState } from "react";
import type { Mode } from "../api";

interface Props {
  loading: boolean;
  onLoad: (url: string, mode: Mode) => void;
}

export function UrlBar({ loading, onLoad }: Props) {
  const [url, setUrl] = useState("");
  const [mode, setMode] = useState<Mode>("auto");

  function submit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = url.trim();
    if (trimmed) onLoad(trimmed, mode);
  }

  return (
    <form className="urlbar" onSubmit={submit}>
      <input
        className="urlbar__input"
        type="url"
        placeholder="https://example.com"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        disabled={loading}
        autoFocus
      />
      <select
        className="urlbar__mode"
        value={mode}
        onChange={(e) => setMode(e.target.value as Mode)}
        disabled={loading}
        title="Fetch mode"
      >
        <option value="auto">auto</option>
        <option value="static">static</option>
        <option value="render">render</option>
      </select>
      <button className="btn" type="submit" disabled={loading || !url.trim()}>
        {loading ? "Loading…" : "Load"}
      </button>
    </form>
  );
}
