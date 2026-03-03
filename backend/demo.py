import os
import sys
from typing import Optional, Tuple


# DEMO wrapper for the full Solar Sniper (Energy Edition) backend.
# Apply ONLY the demo limits via env vars, and disable website/pixel crawling.
os.environ.setdefault("DEMO_CITY", "Milano,Ancona")
os.environ.setdefault(
    "DEMO_CATEGORIES",
    "Grossisti,Centri Sportivi,Concessionarie Auto,Agriturismi",
)
os.environ.setdefault("DEMO_MAX_RESULTS", "30")


_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

import main as _main  # noqa: E402


async def _audit_website_noop(website: str):
    try:
        website = _main.normalize_website(website) or website
        html, _final_url = await _main.fetch_html_with_final_url(website)
        email = _main.extract_email_from_html(html or "")
        return _main.AuditSignals(), email
    except Exception:
        return _main.AuditSignals(), None


async def _audit_website_with_status_noop(
    website: str,
) -> Tuple[
    _main.AuditSignals,
    str,
    Optional[float],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[str],
]:
    # DEMO: keep pixel/gtm detection disabled, but allow lightweight email extraction.
    s = _main.AuditSignals(
        has_facebook_pixel=False,
        has_tiktok_pixel=False,
        has_gtm=False,
        has_ssl=False,
        is_mobile_responsive=False,
        missing_instagram=False,
    )

    tech_stack = "Custom HTML"
    email: Optional[str] = None
    status: Optional[int] = 200
    err: Optional[str] = None
    html: Optional[str] = None
    try:
        website = _main.normalize_website(website) or website
        html, final_url, status, err, _elapsed_s = await _main.fetch_html_with_final_url_and_status(website)
        if final_url:
            s.has_ssl = final_url.lower().startswith("https://")
        if html:
            email = _main.extract_email_from_html(html)
    except Exception:
        pass

    return (
        s,
        tech_stack,
        None,
        None,
        None,
        email,
        status,
        err,
        html,
        None,
        None,
    )


_main.audit_website = _audit_website_noop  # type: ignore
_main.audit_website_with_status = _audit_website_with_status_noop  # type: ignore


APP_TITLE = "SOLAR SNIPER - Energy Lead Extractor"
app = _main.app


if __name__ == "__main__":
    import socket
    import threading
    import webbrowser

    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8010"))
    ui_url = f"http://127.0.0.1:{port}"

    def _is_port_listening(h: str, p: int) -> bool:
        try:
            with socket.create_connection((h, p), timeout=0.25):
                return True
        except OSError:
            return False

    print(f"{APP_TITLE} running on {ui_url}")

    if _is_port_listening("127.0.0.1", port) or _is_port_listening("localhost", port):
        try:
            webbrowser.open_new(ui_url)
        except Exception:
            pass
        raise SystemExit(0)

    def _open_browser() -> None:
        try:
            webbrowser.open_new(ui_url)
        except Exception:
            pass

    try:
        threading.Timer(1.5, _open_browser).start()
    except Exception:
        pass

    uvicorn.run(app, host=host, port=port, log_level="info")
