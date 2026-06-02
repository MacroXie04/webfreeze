# webfreeze

Freeze any webpage into a fully self-contained single HTML file — all CSS, images, and fonts inlined, so it opens completely even offline.

## Features

- **Static Mode**: Fast fetching using `requests`.
- **Rendered Mode**: Fully executes JavaScript using `playwright` to capture the live DOM.
- **Auto Mode**: Automatically switches to rendered mode if the page appears to be a Single Page Application (SPA).
- **Resource Inlining**: Base64 inlining for images, fonts, and recursive CSS `@import` rules.
- **Dynamic Content**: Auto-scrolling to trigger lazy-loaded content.
- **Script Neutralization**: Strips scripts in rendered mode to ensure the snapshot remains stable.
- **Batch Processing**: Process multiple URLs concurrently.

## Installation

```bash
pip install .
playwright install
```

## Usage

```bash
# Basic usage
webfreeze https://example.com -o example.html

# Rendered mode for SPAs
webfreeze https://reactjs.org --render --inline-images

# Batch mode
webfreeze --batch urls.txt --out-dir ./output/ --concurrency 4
```

## Options

- `--static`: Force static fetching (requests).
- `--render`: Force rendered fetching (playwright).
- `--auto`: Automatically detect if rendering is needed (default).
- `--inline-images`: Convert all images and CSS resources to base64.
- `--wait-for <selector>`: Wait for a specific element before capturing.
- `--no-scroll`: Disable automatic scrolling during rendering.
- `--keep-js`: Do not strip `<script>` tags in rendered mode.

## Visual picker (web UI)

A browser-based tool to **load a page, click-select the parts you want, and export a
self-contained HTML of just those parts** — while preserving interactions where
possible.

```bash
# 1. Install the web extras
pip install ".[web]"
playwright install

# 2. Build the React UI (one-time, or after frontend changes)
npm --prefix web install
npm --prefix web run build

# 3. Launch — opens the browser at http://127.0.0.1:8000
webfreeze-serve
```

During development you can instead run the API and the Vite dev server separately:

```bash
webfreeze-serve --no-open          # backend on :8000
npm --prefix web run dev           # UI on :5173 (proxies /api + /proxy to :8000)
```

**Flow:** enter a URL → the page loads live in an iframe (drawers/accordions stay
interactive) → click **Pick** and select elements (use ↑/↓ to grow/shrink the
selection) → **Export HTML**. With no selection, the whole page is exported.

**JS fidelity** (export option):

- `off` — strip all JavaScript (smallest, most stable; like the CLI default).
- `css` — convert recognized widgets (ARIA disclosures → `<details>`, ARIA tabs →
  a radio `:checked` hack) to **pure CSS** so they still work offline with zero JS.
- `css+js` — keep the original JavaScript (external scripts inlined) for widgets
  that can't be converted. Kept scripts may depend on the network and might not run
  fully offline; each is labeled in the fidelity report. Only use on trusted sites.

Every export embeds a `webfreeze fidelity report` HTML comment listing what was
converted or kept.

### Security

The service binds to `127.0.0.1` only. The resource proxy blocks non-HTTP(S)
schemes and any host resolving to a private/loopback/link-local/metadata address
(SSRF protection). To freeze a local dev server, set `WEBFREEZE_ALLOW_PRIVATE=1`.
