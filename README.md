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
