import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


@dataclass
class TechnicalIssue:
    code: str
    severity: str
    message: str
    line: Optional[int] = None
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "context": self.context,
        }


def _find_line_number(html: str, needle: str) -> Optional[int]:
    if not html or not needle:
        return None
    idx = html.lower().find(needle.lower())
    if idx < 0:
        return None
    return html[:idx].count("\n") + 1


def _extract_context(html: str, needle: str, radius: int = 180) -> Optional[str]:
    if not html or not needle:
        return None
    idx = html.lower().find(needle.lower())
    if idx < 0:
        return None
    start = max(0, idx - radius)
    end = min(len(html), idx + len(needle) + radius)
    snippet = html[start:end]
    snippet = snippet.replace("\r\n", "\n").replace("\r", "\n")
    return snippet.strip()


def fetch_homepage_html(url: str, timeout_s: float = 14.0) -> Tuple[str, str, int]:
    r = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=timeout_s,
        allow_redirects=True,
    )
    final_url = str(getattr(r, "url", "") or url)
    status = int(getattr(r, "status_code", 0) or 0)
    return final_url, (r.text or ""), status


def run_technical_audit(url: str, timeout_s: float = 14.0) -> Dict[str, Any]:
    final_url, html, status = fetch_homepage_html(url, timeout_s=timeout_s)

    issues: List[TechnicalIssue] = []
    soup = BeautifulSoup(html or "", "html.parser")

    title = soup.find("title")
    if title is None or not (title.get_text() or "").strip():
        needle = "<title" if title is None else str(title)
        issues.append(
            TechnicalIssue(
                code="SEO_MISSING_TITLE",
                severity="critical",
                message="SEO: tag <title> mancante o vuoto.",
                line=_find_line_number(html, "<title"),
                context=_extract_context(html, "<title"),
            )
        )

    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.IGNORECASE)})
    meta_desc_content = (meta_desc.get("content") if meta_desc else "") or ""
    if meta_desc is None or not meta_desc_content.strip():
        issues.append(
            TechnicalIssue(
                code="SEO_MISSING_META_DESCRIPTION",
                severity="critical",
                message='SEO: <meta name="description"> mancante o vuoto.',
                line=_find_line_number(html, "name=\"description\"")
                or _find_line_number(html, "name='description'")
                or _find_line_number(html, "description"),
                context=_extract_context(html, "description"),
            )
        )

    viewport = soup.find("meta", attrs={"name": re.compile(r"^viewport$", re.IGNORECASE)})
    if viewport is None:
        issues.append(
            TechnicalIssue(
                code="MOBILE_MISSING_VIEWPORT",
                severity="critical",
                message='ERRORE CRITICO: Viewport mancante. Il sito non è ottimizzato per mobile (es. iPhone).',
                line=_find_line_number(html, "viewport"),
                context=_extract_context(html, "viewport"),
            )
        )

    parsed_final = urlparse(final_url)
    is_https = parsed_final.scheme.lower() == "https"
    if is_https:
        mixed: List[Tuple[str, str]] = []
        for tag, attr in (("script", "src"), ("img", "src"), ("link", "href")):
            for el in soup.find_all(tag):
                val = (el.get(attr) or "").strip()
                if not val:
                    continue
                abs_url = urljoin(final_url, val)
                if abs_url.lower().startswith("http://"):
                    mixed.append((tag, abs_url))

        if mixed:
            first_tag, first_url = mixed[0]
            issues.append(
                TechnicalIssue(
                    code="SECURITY_MIXED_CONTENT",
                    severity="critical",
                    message=f"Security: Mixed Content. Risorsa caricata in HTTP su pagina HTTPS ({first_tag}: {first_url}).",
                    line=_find_line_number(html, "http://"),
                    context=_extract_context(html, "http://"),
                )
            )

    return {
        "url": url,
        "final_url": final_url,
        "http_status": status,
        "issues": [i.to_dict() for i in issues],
        "has_critical": any(i.severity == "critical" for i in issues),
    }
