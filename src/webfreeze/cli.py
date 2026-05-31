import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Optional

import click
import requests

from .cache import ResourceCache
from .detector import should_render
from .fetchers.rendered import RenderedFetcher
from .fetchers.static import StaticFetcher
from .inliner import Inliner
from .utils import log_error, log_info, log_success, log_warn, save_html

def process_single(
    url: str,
    output_path: str,
    mode: str,
    inline_images: bool,
    wait_for: Optional[str],
    wait_timeout: int,
    scroll: bool,
    keep_js: bool,
    cache: ResourceCache,
):
    """Process a single URL and save the frozen HTML."""
    try:
        log_info(f"Processing: {url}")
        
        # 1. Initial fetch (static) to determine mode if 'auto'
        static_fetcher = StaticFetcher(cache.session)
        
        final_html = ""
        fetch_mode = mode
        
        if mode == "auto":
            raw_html = static_fetcher.fetch(url)
            if should_render(raw_html):
                log_info("SPA/Dynamic content detected. Switching to RENDER mode.")
                fetch_mode = "render"
            else:
                log_info("Static content detected. Using STATIC mode.")
                fetch_mode = "static"
                final_html = raw_html

        if fetch_mode == "static":
            if not final_html:
                final_html = static_fetcher.fetch(url)
        else:
            rendered_fetcher = RenderedFetcher(
                wait_for=wait_for,
                timeout=wait_timeout,
                scroll=scroll,
                keep_js=keep_js,
            )
            final_html = rendered_fetcher.fetch(url)

        # 2. Inlining
        inliner = Inliner(cache, inline_images=inline_images)
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(final_html, "html.parser")
        inliner.process_soup(soup, url)

        # 3. Save
        save_html(soup, output_path)
        log_success(f"Saved: {output_path} ({os.path.getsize(output_path) // 1024} KB)")

    except Exception as e:
        log_error(f"Failed to process {url}: {e}")

@click.command()
@click.argument("url", required=False)
@click.option("-o", "--output", help="Output filename (for single URL).")
@click.option("--static", "mode", flag_value="static", help="Force static mode.")
@click.option("--render", "mode", flag_value="render", help="Force rendered mode.")
@click.option("--auto", "mode", flag_value="auto", default=True, help="Auto-detect mode (default).")
@click.option("--inline-images", is_flag=True, help="Inline images and CSS resources as base64.")
@click.option("--wait-for", help="CSS selector to wait for in rendered mode.")
@click.option("--wait-timeout", type=int, default=30000, help="Wait timeout in milliseconds.")
@click.option("--no-scroll", is_flag=True, help="Disable auto-scrolling in rendered mode.")
@click.option("--keep-js", is_flag=True, help="Keep <script> tags in rendered mode.")
@click.option("--batch", type=click.Path(exists=True), help="Path to a file containing URLs (one per line).")
@click.option("--out-dir", type=click.Path(), default=".", help="Output directory for batch mode.")
@click.option("--concurrency", type=int, default=4, help="Number of concurrent fetches.")
def main(
    url: Optional[str],
    output: Optional[str],
    mode: str,
    inline_images: bool,
    wait_for: Optional[str],
    wait_timeout: int,
    no_scroll: bool,
    keep_js: bool,
    batch: Optional[str],
    out_dir: str,
    concurrency: int,
):
    """Freeze any webpage into a fully self-contained single HTML file."""
    
    if not url and not batch:
        log_error("You must provide either a URL or a --batch file.")
        return

    # Shared cache and session
    cache = ResourceCache()
    scroll = not no_scroll

    if batch:
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        urls = []
        with open(batch, "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        log_info(f"Batch mode: {len(urls)} URLs, concurrency={concurrency}")
        
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            for i, target_url in enumerate(urls):
                safe_name = "".join(c if c.isalnum() else "_" for c in target_url.split("//")[-1])
                if not safe_name.endswith(".html"):
                    safe_name += ".html"
                out_path = os.path.join(out_dir, safe_name)
                
                executor.submit(
                    process_single,
                    target_url,
                    out_path,
                    mode,
                    inline_images,
                    wait_for,
                    wait_timeout,
                    scroll,
                    keep_js,
                    cache,
                )
    else:
        out_path = output or "frozen_page.html"
        process_single(
            url,
            out_path,
            mode,
            inline_images,
            wait_for,
            wait_timeout,
            scroll,
            keep_js,
            cache,
        )

if __name__ == "__main__":
    main()
