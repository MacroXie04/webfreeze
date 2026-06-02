import { forwardRef } from "react";

interface Props {
  previewUrl: string | null;
}

// The preview iframe is same-origin (served via the backend/proxy), so a later
// phase can read its contentDocument directly for picking. For P1 it simply
// renders the interactive page.
export const PreviewFrame = forwardRef<HTMLIFrameElement, Props>(
  ({ previewUrl }, ref) => {
    if (!previewUrl) {
      return (
        <div className="preview preview--empty">
          <p>Enter a URL above to load a page.</p>
        </div>
      );
    }
    return (
      <iframe
        ref={ref}
        className="preview"
        src={previewUrl}
        title="preview"
      />
    );
  },
);

PreviewFrame.displayName = "PreviewFrame";
