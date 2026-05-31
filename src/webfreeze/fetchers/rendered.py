import time
from typing import Optional

from playwright.sync_api import sync_playwright

from ..utils import log_info, log_warn
from .base import BaseFetcher

class RenderedFetcher(BaseFetcher):
    """
    Fetcher that uses Playwright to render JavaScript and capture the live DOM.
    """

    def __init__(
        self,
        wait_for: Optional[str] = None,
        timeout: int = 30000,
        scroll: bool = True,
        keep_js: bool = False,
    ):
        self.wait_for = wait_for
        self.timeout = timeout
        self.scroll = scroll
        self.keep_js = keep_js

    def fetch(self, url: str) -> str:
        """Render the page and return the processed HTML."""
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            # Use a realistic viewport
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            try:
                log_info(f"Navigating to {url}...")
                page.goto(url, wait_until="networkidle", timeout=self.timeout)

                if self.wait_for:
                    log_info(f"Waiting for selector: {self.wait_for}")
                    page.wait_for_selector(self.wait_for, timeout=self.timeout)

                if self.scroll:
                    log_info("Scrolling to trigger lazy-loaded content...")
                    self._auto_scroll(page)
                    # Wait a bit after scroll for network to settle
                    page.wait_for_load_state("networkidle")

                # Extract runtime-injected CSS (CSS-in-JS, dynamically added <style>)
                log_info("Extracting runtime styles...")
                runtime_styles = page.evaluate("""
                    () => {
                        const styles = [];
                        for (const sheet of document.styleSheets) {
                            try {
                                if (!sheet.href) { // Only dynamic or internal
                                    let rules = '';
                                    for (const rule of sheet.cssRules) {
                                        rules += rule.cssText + '\\n';
                                    }
                                    styles.push(rules);
                                }
                            } catch (e) {
                                // Ignore CORS restricted sheets; Inliner will fetch them server-side
                            }
                        }
                        return styles;
                    }
                """)

                content = page.content()
                soup = self.to_soup(content)

                # Inject extracted runtime styles
                if runtime_styles:
                    for css in runtime_styles:
                        if css.strip():
                            style_tag = soup.new_tag("style")
                            style_tag.string = css
                            if soup.head:
                                soup.head.append(style_tag)
                            else:
                                soup.insert(0, style_tag)

                # Neutralize scripts
                if not self.keep_js:
                    log_info("Neutralizing scripts for static snapshot...")
                    for script in soup.find_all("script"):
                        script.decompose()
                    
                    # Also strip inline event handlers
                    for tag in soup.find_all(True):
                        attrs = list(tag.attrs.keys())
                        for attr in attrs:
                            if attr.lower().startswith("on"):
                                del tag[attr]
                    
                    # Strip <noscript> tags
                    for noscript in soup.find_all("noscript"):
                        noscript.decompose()

                return str(soup)

            except Exception as e:
                log_warn(f"Rendering failed for {url}: {e}")
                raise
            finally:
                browser.close()

    def _auto_scroll(self, page):
        """Scroll to the bottom of the page in steps."""
        page.evaluate("""
            async () => {
                await new Promise((resolve) => {
                    let totalHeight = 0;
                    let distance = 200;
                    let timer = setInterval(() => {
                        let scrollHeight = document.body.scrollHeight;
                        window.scrollBy(0, distance);
                        totalHeight += distance;
                        if (totalHeight >= scrollHeight || totalHeight > 10000) {
                            clearInterval(timer);
                            resolve();
                        }
                    }, 100);
                });
            }
        """)
