export type JsFidelity = "off" | "css";

interface Props {
  jsFidelity: JsFidelity;
  disabled: boolean;
  onChange: (value: JsFidelity) => void;
}

export function OptionsPanel({ jsFidelity, disabled, onChange }: Props) {
  return (
    <label className="opt" title="How interactive widgets are handled on export">
      JS fidelity:
      <select
        value={jsFidelity}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value as JsFidelity)}
      >
        <option value="off">off — strip JS</option>
        <option value="css">css — convert to CSS</option>
      </select>
    </label>
  );
}
