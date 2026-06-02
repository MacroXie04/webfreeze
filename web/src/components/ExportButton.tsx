interface Props {
  disabled: boolean;
  exporting: boolean;
  onExport: () => void;
}

export function ExportButton({ disabled, exporting, onExport }: Props) {
  return (
    <button className="btn btn--primary" onClick={onExport} disabled={disabled || exporting}>
      {exporting ? "Exporting…" : "Export HTML"}
    </button>
  );
}
