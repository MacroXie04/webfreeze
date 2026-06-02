interface Props {
  active: boolean;
  pickMode: boolean;
  count: number;
  breadcrumb: string;
  onTogglePick: () => void;
  onParent: () => void;
  onChild: () => void;
  onClear: () => void;
}

export function PickerToolbar({
  active,
  pickMode,
  count,
  breadcrumb,
  onTogglePick,
  onParent,
  onChild,
  onClear,
}: Props) {
  return (
    <div className="picker">
      <button
        className={"btn" + (pickMode ? " btn--primary" : "")}
        onClick={onTogglePick}
        disabled={!active}
        title="Toggle click-to-select on the page"
      >
        {pickMode ? "Picking…" : "Pick"}
      </button>
      <span className="picker__count">{count} selected</span>
      <button className="btn" onClick={onParent} disabled={!active || count === 0} title="Select parent">
        ↑
      </button>
      <button className="btn" onClick={onChild} disabled={!active || count === 0} title="Select first child">
        ↓
      </button>
      <button className="btn" onClick={onClear} disabled={!active || count === 0}>
        clear
      </button>
      <span className="picker__crumb" title={breadcrumb}>
        {breadcrumb}
      </span>
    </div>
  );
}
