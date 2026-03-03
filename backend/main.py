import asyncio
import base64
import csv
import io
import json
import math
import os
import hashlib
import random
import re
import sys
import time
import traceback
import urllib.parse
import uuid
import html as _html
import threading
import socket
from urllib.parse import quote
from urllib.parse import urlparse
from datetime import date, datetime
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Tuple

from audit_engine import run_technical_audit
from report_generator import generate_audit_pdf

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
except Exception:  # pragma: no cover
    Fore = None  # type: ignore
    Style = None  # type: ignore

# Windows: Playwright spawns browser subprocesses. SelectorEventLoop on Windows
# does NOT support subprocess; ensure Proactor is used.
if os.name == "nt":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

import httpx
from bs4 import BeautifulSoup
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

try:
    import whois as _whois  # type: ignore
except Exception:  # pragma: no cover
    _whois = None

try:
    from playwright.async_api import async_playwright
except Exception:  # pragma: no cover
    async_playwright = None

try:
    from playwright.sync_api import sync_playwright
except Exception:  # pragma: no cover
    sync_playwright = None


_LEAD_HISTORY_LOCK = threading.Lock()


def _lead_history_path() -> str:
    # Persist next to the executable in PyInstaller builds; otherwise next to this file.
    try:
        if getattr(sys, "frozen", False) and getattr(sys, "executable", None):
            base_dir = os.path.dirname(os.path.abspath(sys.executable))
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
    except Exception:
        base_dir = os.getcwd()
    return os.path.join(base_dir, "lead_history.json")


def _normalize_phone_id(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    p = str(phone).strip()
    if not p:
        return None
    # Keep only digits and leading '+' (if present)
    keep_plus = p.startswith("+")
    digits = re.sub(r"\D+", "", p)
    if not digits:
        return None
    return ("+" if keep_plus else "") + digits


def _make_lead_id(business_name: Optional[str], address: Optional[str], phone: Optional[str]) -> str:
    phone_id = _normalize_phone_id(phone)
    if phone_id:
        return f"tel:{phone_id}"
    name_part = (business_name or "").strip().lower()
    addr_part = (address or "").strip().lower()
    return f"na:{name_part}|{addr_part}"


def _load_lead_history() -> set[str]:
    path = _lead_history_path()
    with _LEAD_HISTORY_LOCK:
        try:
            if not os.path.exists(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump([], f)
                except Exception:
                    pass
                return set()
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {str(x) for x in data if str(x).strip()}
        except Exception:
            return set()
    return set()


def _append_lead_history(lead_id: str) -> None:
    if not lead_id:
        return
    path = _lead_history_path()
    with _LEAD_HISTORY_LOCK:
        try:
            existing: List[str] = []
            try:
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        if isinstance(d, list):
                            existing = [str(x) for x in d]
            except Exception:
                existing = []

            if lead_id in set(existing):
                return
            existing.append(lead_id)

            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            # Best-effort persistence; don't break the job if history can't be written.
            return


class StartJobRequest(BaseModel):
    category: str = Field(min_length=2, max_length=120)
    city: str = Field(min_length=2, max_length=120)
    zone: Optional[str] = None


class AuditSignals(BaseModel):
    has_facebook_pixel: bool = False
    has_tiktok_pixel: bool = False
    has_gtm: bool = False
    has_ssl: bool = False
    is_mobile_responsive: bool = False
    missing_instagram: bool = False


class BusinessResult(BaseModel):
    result_index: int
    business_name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    website_status: Literal["HAS_WEBSITE", "MISSING_WEBSITE"]
    tech_stack: str = "Custom HTML"
    load_speed_s: Optional[float] = None
    load_speed: Optional[float] = None
    domain_creation_date: Optional[str] = None
    domain_expiration_date: Optional[str] = None
    website_http_status: Optional[int] = None
    website_error: Optional[str] = None
    website_has_html: bool = False
    website_error_line: Optional[int] = None
    website_error_hint: Optional[str] = None
    instagram_missing: Optional[bool] = None
    tiktok_missing: Optional[bool] = None
    pixel_missing: Optional[bool] = None
    solar_score: int = 0
    solar_potential_bucket: Literal["LOW", "GOOD", "EXCELLENT"] = "LOW"
    roof_type: str = "Residenziale"
    plant_estimate: str = ""
    estimated_area_m2: Optional[int] = None
    estimated_kwp: Optional[int] = None
    annual_kwh: Optional[int] = None
    annual_co2_tons: Optional[float] = None
    annual_savings_eur: Optional[int] = None
    payback_years: Optional[float] = None
    business_case: Optional[str] = None
    diamond_target: Optional[bool] = None
    whatsapp_message: Optional[str] = None
    audit: AuditSignals


class JobStatus(BaseModel):
    id: str
    state: Literal["queued", "running", "done", "error"]
    progress: int
    message: str
    started_at: float
    finished_at: Optional[float] = None
    error: Optional[str] = None
    results_count: int = 0


@dataclass
class Job:
    id: str
    category: str
    city: str
    zone: Optional[str] = None
    state: str = "queued"
    progress: int = 0
    message: str = "Queued"
    started_at: float = field(default_factory=lambda: time.time())
    finished_at: Optional[float] = None
    error: Optional[str] = None
    results: List[BusinessResult] = field(default_factory=list)
    events: asyncio.Queue = field(default_factory=asyncio.Queue)
    site_html: Dict[int, str] = field(default_factory=dict)
    technical_audits: Dict[int, Dict[str, Any]] = field(default_factory=dict)

    async def emit(self, progress: int, message: str) -> None:
        self.progress = max(0, min(100, progress))
        self.message = message
        await self.events.put(
            {
                "progress": self.progress,
                "message": message,
                "state": self.state,
                "error": self.error,
                "results_count": len(self.results),
            }
        )


JOBS: Dict[str, Job] = {}

app = FastAPI(title="Lead Gen & Audit Backend", version="0.1.0")


def _get_frontend_out_dir() -> str:
    # DEV vs PyInstaller frozen runtime
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", "")
        return os.path.join(str(base), "frontend", "out")
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "out"))


_FRONTEND_OUT_DIR = _get_frontend_out_dir()
_HAS_FRONTEND_OUT = os.path.isdir(_FRONTEND_OUT_DIR) and os.path.isfile(
    os.path.join(_FRONTEND_OUT_DIR, "index.html")
)

if not _HAS_FRONTEND_OUT:
    print(f"CRITICAL: Frontend path not found at {_FRONTEND_OUT_DIR}")

_allow_all = os.getenv("CORS_ALLOW_ALL", "1") == "1"

_demo_city_raw = (os.getenv("DEMO_CITY") or "").strip()
_demo_cities = [c.strip() for c in _demo_city_raw.split(",") if c.strip()]
_demo_city = _demo_cities[0] if _demo_cities else ""
_demo_categories_raw = (os.getenv("DEMO_CATEGORIES") or "").strip()
_demo_categories = [c.strip() for c in _demo_categories_raw.split(",") if c.strip()]
try:
    _demo_max_results = int((os.getenv("DEMO_MAX_RESULTS") or "0").strip() or "0")
except Exception:
    _demo_max_results = 0

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    # IMPORTANT: browsers disallow '*' with credentials. For local standalone we don't need cookies.
    allow_credentials=False,
    allow_methods=["*"] ,
    allow_headers=["*"],
)


if _HAS_FRONTEND_OUT:
    app.mount(
        "/_next",
        StaticFiles(directory=os.path.join(_FRONTEND_OUT_DIR, "_next")),
        name="next-assets",
    )


PIXEL_PATTERNS = {
    "facebook": re.compile(r"fbevents\\.js", re.IGNORECASE),
    "tiktok": re.compile(r"tiktok\\.com/i18n/pixel", re.IGNORECASE),
    "gtm": re.compile(r"googletagmanager\\.com", re.IGNORECASE),
}


async def fetch_html(url: str) -> str:
    raise RuntimeError("fetch_html signature changed; use fetch_html_with_final_url")


async def fetch_html_with_final_url(url: str) -> Tuple[str, str]:
    timeout = httpx.Timeout(8.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        return r.text, str(r.url)


async def fetch_html_with_final_url_and_status(
    url: str,
) -> Tuple[Optional[str], str, Optional[int], Optional[str], Optional[float]]:
    timeout = httpx.Timeout(8.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=False) as client:
        try:
            t0 = time.perf_counter()
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            status = int(getattr(r, "status_code", 0) or 0)
            final_url = str(r.url)
            elapsed_s: Optional[float] = None
            try:
                elapsed = getattr(r, "elapsed", None)
                if elapsed is not None:
                    elapsed_s = round(float(elapsed.total_seconds()), 2)
            except Exception:
                elapsed_s = None
            if elapsed_s is None:
                try:
                    elapsed_s = round(float(time.perf_counter() - t0), 2)
                except Exception:
                    elapsed_s = None
            # Return body even on errors (many sites serve an error page HTML)
            if status >= 400:
                return r.text, final_url, status, f"HTTP {status}", elapsed_s
            return r.text, final_url, status, None, elapsed_s
        except httpx.HTTPStatusError as e:
            try:
                status = int(getattr(e.response, "status_code", 0) or 0)
                final_url = str(getattr(e.response, "url", "") or url)
            except Exception:
                status = None
                final_url = url
            return None, final_url, status, f"HTTP {status}" if status else str(e), None
        except Exception as e:
            return None, url, None, str(e), None


def _coerce_date_to_iso(d: Any) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, list) and d:
        d = d[0]
    if isinstance(d, datetime):
        return d.date().isoformat()
    if isinstance(d, date):
        return d.isoformat()
    try:
        s = str(d).strip()
        return s or None
    except Exception:
        return None


def _extract_domain_from_url(url: str) -> Optional[str]:
    try:
        host = urlparse(url).hostname
        if not host:
            return None
        host = host.strip().lower()
        if host.startswith("www."):
            host = host[4:]
        return host or None
    except Exception:
        return None


async def fetch_solar_analysis(lat: float, lon: float) -> Dict[str, Any]:
    api_key = os.getenv("GOOGLE_SOLAR_API_KEY", "")
    if not api_key:
        raise RuntimeError("GOOGLE_SOLAR_API_KEY non configurata")
    
    url = (
        "https://solar.googleapis.com/v1/buildingInsights:findClosest"
        f"?location.latitude={lat}&location.longitude={lon}"
        f"&requiredQuality=HIGH&key={api_key}"
    )
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url)
        if r.status_code == 404:
            raise RuntimeError("Edificio non trovato nel database Solar API")
        r.raise_for_status()
        data = r.json()
    
    solar = data.get("solarPotential", {})
    stats = solar.get("wholeRoofStats", {})
    
    return {
        "max_panels": solar.get("maxArrayPanelsCount"),
        "max_area_m2": round(solar.get("maxArrayAreaMeters2", 0), 1),
        "sunshine_hours_year": round(solar.get("maxSunshineHoursPerYear", 0)),
        "roof_area_m2": round(stats.get("areaMeters2", 0), 1),
        "carbon_offset_kg_per_mwh": solar.get("carbonOffsetFactorKgPerMwh"),
        "panel_configs": [
            {
                "panels": c.get("panelsCount"),
                "kwp": round(c.get("yearlyEnergyDcKwh", 0) / 1000, 1),
                "yearly_kwh": round(c.get("yearlyEnergyDcKwh", 0)),
            }
            for c in (solar.get("solarPanelConfigs") or [])[-3:]  # ultimi 3 (max potenza)
        ],
        "imagery_date": data.get("imageryDate"),
        "imagery_quality": data.get("imageryQuality"),
        "center": data.get("center"),
    }


def normalize_website(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    u = url.strip()
    if not u:
        return None
    if not u.startswith("http://") and not u.startswith("https://"):
        u = "https://" + u
    return u


def clean_phone(raw_phone):
    if not raw_phone:
        return None, False

    num = re.sub(r"[^\d+]", "", str(raw_phone))

    if num.startswith("+39"):
        num = num[3:]
    elif num.startswith("0039"):
        num = num[4:]

    if not num:
        return None, False

    if num.startswith("0"):
        if num.startswith("00"):
            num = num[1:]
        return num, False
    elif num.startswith("3"):
        return num, True
    return num, False


def extract_phone_from_html(soup):
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].lower()
        if "tel:" in href or "wa.me/" in href or "api.whatsapp.com/send" in href:
            raw_number = (
                href.replace("tel:", "")
                .replace("https://wa.me/", "")
                .replace("http://wa.me/", "")
                .split("?")[0]
            )
            num = re.sub(r"[^\d+]", "", raw_number)
            if num:
                return num
    try:
        text = soup.get_text(" ", strip=True)
    except Exception:
        text = ""
    m = re.search(r"\b(3[2-9]\d{1}\s?\d{3}\s?\d{3,4})\b", text or "")
    if m:
        cand = m.group(1)
        if cand and not str(cand).startswith("0"):
            return cand
    return None


def normalize_phone_italy_first(raw: Optional[str]) -> Optional[str]:
    num, _is_mobile = clean_phone(raw)
    return num


def _clean_phone_minimal(value: str) -> str:
    # Only remove spaces and hyphens as requested (do NOT strip other characters aggressively).
    return (value or "").replace(" ", "").replace("-", "")


def _normalize_it_mobile_strict(raw: str) -> Optional[str]:
    # Accept only Italian mobile numbers:
    # - optional +39 / 0039
    # - then 3[2-9]xxxxxxxx (10 digits after 39)
    try:
        if not raw:
            return None
        s = _clean_phone_minimal(raw)

        # Extract digits for validation; we keep '+' only for formatting later.
        digits = re.sub(r"\D+", "", s)
        if not digits:
            return None

        # Handle 0039 prefix
        if digits.startswith("00"):
            digits = digits[2:]

        # If country code present
        if digits.startswith("39"):
            rest = digits[2:]
            if len(rest) != 10:
                return None
            if not re.fullmatch(r"3[2-9]\d{8}", rest):
                return None
            return "+39" + rest

        # No country code: must be exactly 10 digits mobile starting with 3[2-9]
        if len(digits) == 10 and re.fullmatch(r"3[2-9]\d{8}", digits):
            return "+39" + digits

        return None
    except Exception:
        return None


def _deep_crawl_mobile_from_website_sync(website: str) -> Optional[str]:
    # DEMO-only helper: fetch homepage + contacts page quickly and try to find a phone number.
    try:
        root = normalize_website(website) or website
        if not root:
            return None

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        # Strict budget: at most 2 requests; ~3.5s each.
        timeout = httpx.Timeout(3.5, connect=2.0)
        paths = ["", "/contatti", "/contact"]

        with httpx.Client(
            follow_redirects=True,
            timeout=timeout,
            verify=False,
            headers=headers,
        ) as client:
            fetched = 0
            for p in paths:
                if fetched >= 2:
                    break
                url = root.rstrip("/") + p
                try:
                    r = client.get(url)
                    fetched += 1
                    if int(getattr(r, "status_code", 0) or 0) >= 400:
                        continue
                    html = r.text or ""
                    if not html.strip():
                        continue

                    try:
                        soup = BeautifulSoup(html, "html.parser")
                        raw = extract_phone_from_html(soup)
                        if raw:
                            num, _is_mobile = clean_phone(raw)
                            if num:
                                return num
                    except Exception:
                        pass
                except Exception:
                    continue

        return None
    except Exception:
        return None


def audit_from_html(html: str) -> AuditSignals:
    s = AuditSignals()
    if PIXEL_PATTERNS["facebook"].search(html):
        s.has_facebook_pixel = True
    if PIXEL_PATTERNS["tiktok"].search(html):
        s.has_tiktok_pixel = True
    if PIXEL_PATTERNS["gtm"].search(html):
        s.has_gtm = True

    soup = BeautifulSoup(html, "html.parser")

    has_insta = False
    try:
        if "instagram.com" in (html or "").lower():
            has_insta = True
    except Exception:
        pass
    try:
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip().lower()
            if "instagram.com" in href:
                has_insta = True
                break
    except Exception:
        has_insta = False
    s.missing_instagram = not has_insta

    viewport = soup.find("meta", attrs={"name": re.compile(r"viewport", re.IGNORECASE)})
    s.is_mobile_responsive = viewport is not None
    return s


def detect_tech_stack(html: str) -> str:
    lower = (html or "").lower()
    # WordPress
    if (
        "/wp-content/" in lower
        or "/wp-includes/" in lower
        or 'name="generator" content="wordpress' in lower
        or "wp-emoji-release.min.js" in lower
    ):
        return "WordPress"

    # Wix
    if (
        "wix.com" in lower
        or "x-wix-request-id" in lower
        or "wixsite" in lower
        or "wixdata" in lower
        or "wix-ui" in lower
        or "id=\"comp-" in lower
        or "id='comp-" in lower
        or " comp-" in lower
    ):
        return "Wix"

    # Shopify
    if (
        "cdn.shopify.com" in lower
        or "shopify.theme" in lower
        or "shopify" in lower
        or "myshopify.com" in lower
        or "shopifyanalytics" in lower
    ):
        return "Shopify"

    # Squarespace
    if "squarespace" in lower or "static1.squarespace.com" in lower:
        return "Squarespace"
    return "Custom HTML"


def extract_email_from_html(html: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select('a[href^="mailto:"]'):
            href = a.get("href") or ""
            if not href.lower().startswith("mailto:"):
                continue
            value = href.split(":", 1)[1].strip()
            value = value.split("?", 1)[0].strip()
            value = value.strip("<>\"' ")
            if not value:
                continue
            if re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", value):
                return value
        text = ""
        try:
            text = soup.get_text(" ", strip=True)
        except Exception:
            text = ""
        blob = " ".join([str(html or ""), str(text or "")])
        m = re.search(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", blob)
        if m:
            return m.group(0)
        return None
    except Exception:
        return None


async def audit_website(website: str) -> Tuple[AuditSignals, Optional[str]]:
    website = normalize_website(website) or website
    signals = AuditSignals()
    for attempt in range(2):
        try:
            html, final_url = await fetch_html_with_final_url(website)
            parsed = audit_from_html(html)
            parsed.has_ssl = final_url.lower().startswith("https://")
            email = extract_email_from_html(html)
            return parsed, email
        except Exception:
            if attempt == 0:
                await asyncio.sleep(0.6)
                continue
            return signals, None


async def audit_website_with_status(
    website: str,
) -> Tuple[
    AuditSignals,
    str,
    Optional[float],
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[str],
    Optional[str],
    Optional[str],
    Optional[int],
    Optional[str],
]:
    website = normalize_website(website) or website
    signals = AuditSignals()
    for attempt in range(2):
        try:
            html, final_url, status, err, elapsed_s = await fetch_html_with_final_url_and_status(website)
            if html is None:
                created, expires = await whois_lookup_dates(final_url)
                return (
                    signals,
                    "Custom HTML",
                    elapsed_s,
                    created,
                    expires,
                    None,
                    status,
                    err,
                    None,
                    None,
                    None,
                )
            # Basic hint/line extraction (best-effort; HTML is not always formatted)
            hint = None
            line = None
            try:
                lower = html.lower()
                if err and isinstance(status, int) and status >= 400:
                    hint = f"HTTP {status}"
                    # try to highlight the most descriptive part of the error page
                    needles = [
                        "<title>",
                        "<h1",
                        "404",
                        "not found",
                        "pagina non trovata",
                        "500",
                        "server error",
                        "bad gateway",
                        "service unavailable",
                        "nginx",
                        "cloudflare",
                        "error",
                    ]
                    idx = -1
                    for n in needles:
                        idx = lower.find(n)
                        if idx >= 0:
                            break
                    if idx >= 0:
                        line = html[:idx].count("\n") + 1
                    else:
                        line = 1
                elif "uncaught" in lower:
                    hint = "Uncaught"
                elif "failed to load resource" in lower:
                    hint = "Failed to load resource"
                if hint:
                    idx = lower.find(hint.lower())
                    if idx >= 0:
                        line = html[:idx].count("\n") + 1
            except Exception:
                hint = None
                line = None
            parsed = audit_from_html(html)
            parsed.has_ssl = final_url.lower().startswith("https://")
            email = extract_email_from_html(html)
            tech_stack = detect_tech_stack(html)
            created, expires = await whois_lookup_dates(final_url)
            return parsed, tech_stack, elapsed_s, created, expires, email, status, err, html, line, hint
        except Exception as e:
            if attempt == 0:
                await asyncio.sleep(0.6)
                continue
            return signals, "Custom HTML", None, None, None, None, None, str(e), None, None, None


def _compose_maps_query(category: str, city: str, zone: Optional[str]) -> str:
    z = (zone or "").strip()
    if not z or z.lower() == "tutta la città".lower():
        return f"{category} {city}"
    return f"{category} {city} {z}"


async def scrape_google_maps_playwright(category: str, city: str, zone: Optional[str] = None) -> List[Dict[str, Any]]:
    # NOTE: On Windows + Python 3.13, Playwright async API may fail with
    # NotImplementedError due to asyncio subprocess limitations.
    # Using sync_playwright inside a thread avoids asyncio subprocess entirely.
    if sync_playwright is None:
        raise RuntimeError("Playwright not installed")

    return await asyncio.to_thread(_scrape_google_maps_sync, category, city, zone)


async def scrape_google_maps_playwright_with_alarm(
    category: str, city: str, zone: Optional[str], alarm_cb
) -> List[Dict[str, Any]]:
    if sync_playwright is None:
        raise RuntimeError("Playwright not installed")
    return await asyncio.to_thread(_scrape_google_maps_sync, category, city, zone, alarm_cb)


def _scrape_google_maps_sync(category: str, city: str, zone: Optional[str] = None, alarm_cb=None) -> List[Dict[str, Any]]:
    base_query = _compose_maps_query(category, city, zone)
    query_variants = [base_query, f"{base_query}, Italia"]
    last_error: Optional[str] = None
    started = time.time()

    lead_historyies= _load_lead_history()
    disable_history_dedup = False
    if _demo_city and _demo_max_results > 0:
        disable_history_dedup = True
        lead_history = set()

    with sync_playwright() as p:
        for attempt, q in enumerate(query_variants, start=1):
            results: List[Dict[str, Any]] = []
            try:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--lang=it-IT",
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                    ],
                )
                context = browser.new_context(
                    locale="it-IT",
                    timezone_id="Europe/Rome",
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1400, "height": 900},
                )
                page = context.new_page()

                def _alarm(url: str, err: str) -> None:
                    try:
                        msg = f"[ALLARME SITO] -> {url} -> {err}"
                        if Fore is not None and Style is not None:
                            print(Style.BRIGHT + Fore.RED + msg + Style.RESET_ALL)
                        else:
                            print("\033[91m\033[1m" + msg + "\033[0m")
                        if alarm_cb is not None:
                            try:
                                alarm_cb(url, err)
                            except Exception:
                                pass
                    except Exception:
                        pass

                def _attach_passive_error_listeners() -> None:
                    try:
                        def should_emit(text: str) -> bool:
                            try:
                                t = (text or "").strip()
                                if not t:
                                    return False
                                if t in {"_.lp", "_.kb"}:
                                    return False
                                if "Failed to load resource" in t:
                                    return True
                                if "Uncaught" in t:
                                    return True
                                return False
                            except Exception:
                                return False

                        def on_console(message) -> None:
                            try:
                                if getattr(message, "type", None) and message.type == "error":
                                    if should_emit(getattr(message, "text", "") or ""):
                                        _alarm(page.url or "(unknown)", message.text)
                            except Exception:
                                pass

                        def on_pageerror(exc) -> None:
                            try:
                                s = str(exc)
                                if should_emit(s):
                                    _alarm(page.url or "(unknown)", s)
                            except Exception:
                                pass

                        def on_response(response) -> None:
                            try:
                                status = int(getattr(response, "status", 0) or 0)
                                if status in (404, 429, 500) or status >= 500:
                                    _alarm(str(getattr(response, "url", "(unknown)")), f"HTTP {status}")
                            except Exception:
                                pass

                        page.on("console", on_console)
                        page.on("pageerror", on_pageerror)
                        page.on("response", on_response)
                    except Exception:
                        pass

                _attach_passive_error_listeners()
                page.set_default_timeout(20000)
                try:
                    page.set_extra_http_headers({"Accept-Language": "it-IT,it;q=0.9,en;q=0.8"})
                except Exception:
                    pass

                def try_handle_consent() -> None:
                    texts = [
                        "Accetta tutto",
                        "Rifiuta tutto",
                        "I agree",
                        "Accept all",
                        "Reject all",
                    ]

                    def click_in_frame(frame) -> bool:
                        # Try common Google consent button id as well
                        try:
                            btn_css = frame.locator('#L2AGLb')
                            if btn_css.count() and btn_css.is_visible():
                                btn_css.click(timeout=2000)
                                page.wait_for_timeout(600)
                                return True
                        except Exception:
                            pass
                        for t in texts:
                            try:
                                btn = frame.get_by_role("button", name=t).first
                                if btn.count() and btn.is_visible():
                                    btn.click(timeout=2500)
                                    page.wait_for_timeout(700)
                                    return True
                            except Exception:
                                continue
                        return False

                    try:
                        if click_in_frame(page):
                            return
                    except Exception:
                        pass

                    for fr in page.frames:
                        try:
                            if fr == page.main_frame:
                                continue
                            if click_in_frame(fr):
                                return
                        except Exception:
                            continue

                search_url = f"https://www.google.com/maps/search/{quote(q)}?hl=it&gl=it&entry=ttu"
                page.goto(search_url, wait_until="domcontentloaded", timeout=55000)
                page.wait_for_timeout(1400)
                try_handle_consent()

                # Guard rail: if we're close to the global 240s timeout, bail out early.
                if time.time() - started > 210:
                    context.close()
                    browser.close()
                    return results

                # Wait for either results or any blocking state
                cards = page.locator('div[role="article"]')
                alt_cards = page.locator('div.Nv2PK')
                for _ in range(18):
                    try_handle_consent()
                    if cards.count() > 0 or alt_cards.count() > 0:
                        break
                    # Sometimes feed appears later; give it a bit more time overall (~10s)
                    page.wait_for_timeout(800)

                # Prefer role=article, otherwise fallback to Nv2PK
                if cards.count() == 0 and alt_cards.count() > 0:
                    cards = alt_cards

                if cards.count() == 0:
                    html = page.content().lower()
                    if "unusual traffic" in html or "captcha" in html:
                        last_error = (
                            "Google blocked the request (captcha/unusual traffic). Try again later or from another network."
                        )
                    else:
                        last_error = (
                            "Google Maps returned 0 results. Trying a slightly different query or city may help."
                        )
                    context.close()
                    browser.close()
                    # Retry with next variant if available
                    if attempt < len(query_variants):
                        time.sleep(1.0)
                        continue
                    raise RuntimeError(last_error)

                # Scroll feed to load more results
                feed = page.locator('div[role="feed"]').first
                # Cap NEW reiesults to avoid long sessions / UI changes causing timeouts.
                cap_new = 50
                if _demo_city and _demo_max_results > 0:
                    cap_new = _demo_max_results

                def _scroll_once() -> None:
                    try:
                        feed.evaluate("(el) => { el.scrollBy(0, 1400); }")
                    except Exception:
                        try:
                            page.mouse.wheel(0, 1200)
                        except Exception:
                            pass
                    page.wait_for_timeout(350)

                # Pre-load some cards
                for _ in range(6):
                    _scroll_once()

                def _normalize_phone_text(value: Optional[str]) -> Optional[str]:
                    if not value:
                        return None
                    v = " ".join(str(value).split())
                    v = re.sub(r"^telefono\s*:??\s*", "", v, flags=re.IGNORECASE)
                    v = v.strip()
                    return v or None

                def _extract_phone_best_effort() -> Optional[str]:
                    # Primary selector (current behavior)
                    try:
                        v = page.locator('button[data-item-id^="phone"]').first.text_content(timeout=1500)
                        nv = _normalize_phone_text(v)
                        if nv:
                            return nv
                    except Exception:
                        pass

                    # Fallback: tel: links (sometimes present in the details panel)
                    try:
                        href = page.locator('a[href^="tel:"]').first.get_attribute("href", timeout=1200)
                        if href:
                            hv = href.split(":", 1)[1]
                            hv = hv.split("?", 1)[0]
                            nv = _normalize_phone_text(hv)
                            if nv:
                                return nv
                    except Exception:
                        pass

                    # Fallback: aria-label buttons
                    aria_candidates = [
                        "button[aria-label*='Telefono']",
                        "button[aria-label*='telefono']",
                        "button[aria-label*='Phone']",
                        "button[aria-label*='phone']",
                    ]
                    for css in aria_candidates:
                        try:
                            v = page.locator(css).first.text_content(timeout=1200)
                            nv = _normalize_phone_text(v)
                            if nv:
                                return nv
                        except Exception:
                            continue

                    return None

                # Keep scrolling until we collect cap_new NEW leads (not in history)
                processed_idx = 0
                scrolls = 0
                max_scrolls = 80

                while len(results) < cap_new:
                    if time.time() - started > 225:
                        break

                    # Recompute cards with fallback logic (Maps sometimes uses Nv2PK blocks)
                    cards = page.locator('div[role="article"]')
                    alt_cards = page.locator('div.Nv2PK')
                    if cards.count() == 0 and alt_cards.count() > 0:
                        cards = alt_cards

                    count_now = cards.count()
                    if processed_idx >= count_now:
                        if scrolls >= max_scrolls:
                            break
                        _scroll_once()
                        scrolls += 1
                        continue

                    # Process newly loaded cards
                    for idx in range(processed_idx, count_now):
                        if len(results) >= cap_new:
                            break
                        if time.time() - started > 225:
                            break

                        card = cards.nth(idx)
                        try:
                            name = (
                                card.locator(".fontHeadlineSmall").first.text_content(timeout=1500) or ""
                            ).strip()
                        except Exception:
                            name = ""
                        if not name:
                            processed_idx = idx + 1
                            continue

                        try:
                            card.click()
                            page.wait_for_timeout(650)
                        except Exception:
                            pass

                        lat = None
                        lon = None
                        try:
                            u = str(page.url or "")
                            m = re.search(r"@(-?\d+\.\d+),(-?\d+\.\d+)", u)
                            if m:
                                lat = float(m.group(1))
                                lon = float(m.group(2))
                        except Exception:
                            lat = None
                            lon = None

                        address = None
                        phone = None
                        website = None

                        try:
                            address = page.locator('button[data-item-id="address"]').first.text_content(timeout=1500)
                        except Exception:
                            address = None

                        try:
                            phone = _extract_phone_best_effort()
                        except Exception:
                            phone = None

                        try:
                            website = page.locator('a[data-item-id="authority"]').first.get_attribute(
                                "href", timeout=1500
                            )
                        except Exception:
                            website = None
                        # DEMO: deep crawl website to find a real mobile number and override Maps phone.
                        if _demo_cities and _demo_max_results > 0 and website:
                            try:
                                mobile = _deep_crawl_mobile_from_website_sync(website)
                                if mobile:
                                    phone = mobile
                            except Exception:
                                pass

                        lead_id = _make_lead_id(name, address.strip() if address else None, phone)
                        if not disable_history_dedup and lead_id in lead_history:
                            print("Già presente in storico - SALTO")
                            processed_idx = idx + 1
                            continue

                        results.append(
                            {
                                "business_name": name,
                                "address": address.strip() if address else None,
                                "lat": lat,
                                "lon": lon,
                                "phone": phone.strip() if phone else None,
                                "website": website,
                                "lead_id": lead_id,
                            }
                        )
                        if not disable_history_dedup:
                            lead_history.add(lead_id)
                        processed_idx = idx + 1

                    # After processing current batch, scroll for more
                    if len(results) < cap_new:
                        if scrolls >= max_scrolls:
                            break
                        _scroll_once()
                        scrolls += 1

                context.close()
                browser.close()

                return results
            except Exception as e:
                try:
                    context.close()
                except Exception:
                    pass
                try:
                    browser.close()
                except Exception:
                    pass
                last_error = str(e) or last_error
                # Small backoff then next variant
                if attempt < len(query_variants):
                    time.sleep(1.0)
                    continue
                raise


async def run_job(job: Job) -> None:
    job.state = "running"
    await job.emit(3, "Scraping Maps...")

    try:
        loop = asyncio.get_running_loop()

        def alarm_cb(url: str, err: str) -> None:
            try:
                asyncio.run_coroutine_threadsafe(
                    job.events.put(
                        {
                            "type": "alarm",
                            "url": url,
                            "error": err,
                            "ts": time.time(),
                        }
                    ),
                    loop,
                )
            except Exception:
                pass

        raw = await scrape_google_maps_playwright_with_alarm(job.category, job.city, job.zone, alarm_cb)

        if not raw:
            raise RuntimeError("No results returned from Google Maps. Try a different query or city.")

        await job.emit(12, f"Trovate {len(raw)} attività. Avvio audit...")

        results: List[BusinessResult] = []
        total = max(1, len(raw))

        def _is_south_city(city: str) -> bool:
            c = (city or "").strip().lower()
            south = {
                "napoli",
                "bari",
                "palermo",
                "catania",
                "salerno",
                "caserta",
                "foggia",
                "lecce",
                "taranto",
                "reggio calabria",
                "catanzaro",
                "cosenza",
                "cagliari",
                "sassari",
                "siracusa",
                "messina",
                "ragusa",
                "trapani",
                "agrigento",
                "crotone",
                "brindisi",
            }
            return c in south

        def _is_high_irradiance_city(city: str) -> bool:
            c = (city or "").strip().lower()
            high = {
                # Center-South & islands (aggressive heuristic)
                "roma",
                "napoli",
                "bari",
                "palermo",
                "catania",
                "salerno",
                "lecce",
                "taranto",
                "cagliari",
                "sassari",
                "messina",
                "siracusa",
                "ragusa",
                "trapani",
                "agrigento",
                "pescara",
                "ancona",
                "perugia",
            }
            return c in high or _is_south_city(city)

        def _compute_solar_score(name: str, city: str, website_html: Optional[str]) -> int:
            score = 0
            n = (name or "").lower()

            # Keyword Gold List (big targets) => force 95+
            gold_keywords = (
                "metro",
                "gross",
                "ingrosso",
                "logistica",
                "deposito",
                "centro",
                "magazzin",
                "magazzini",
            )
            if any(k in n for k in gold_keywords) or ("s.p.a" in n) or (" spa" in n):
                score = max(score, 95)

            # Budget / struttura societaria (power boost)
            has_spa = ("s.p.a" in n) or (" spa" in n)
            has_group = "group" in n
            has_srl = ("s.r.l" in n) or (" srl" in n)

            if has_spa or has_group:
                score += 40
            elif has_srl:
                score += 20

            # Dimensione/Tipologia (tetti grandi)
            if "logistic" in n or "industr" in n or "siderurg" in n:
                score += 40

            # Energivori
            if "hotel" in n or "ristor" in n or "plastica" in n or "carta" in n:
                score += 30

            # Più sole al Sud
            if _is_south_city(city):
                score += 20

            # Alto irraggiamento (Centro-Sud)
            if _is_high_irradiance_city(city):
                score += 10

            # Fatturato (stima) dal sito
            if website_html:
                h = website_html.lower()
                if "spa" in h or "group" in h or "internazional" in h:
                    score += 10

            # Baseline più alta: niente 0/100
            score = max(score, 30)

            return max(0, min(100, int(score)))

        def _roof_type(name: str) -> str:
            n = (name or "").lower()
            if (
                "fabbric" in n
                or "industr" in n
                or "logistic" in n
                or "siderurg" in n
                or "produzion" in n
                or "plastica" in n
                or "carta" in n
            ):
                return "Capannone Industriale"
            if "hotel" in n or "alberg" in n or "supermerc" in n or "ristor" in n or "spa" in n:
                return "Commerciale"
            return "Residenziale"

        def _plant_estimate_from_score(score: int) -> str:
            if score > 90:
                return "STIMA: >200 kWp"
            if score > 70:
                return "STIMA: 80-150 kWp"
            if score > 40:
                return "STIMA: 30-60 kWp"
            return "STIMA: 6-20 kWp"

        def _bucket(score: int) -> Literal["LOW", "GOOD", "EXCELLENT"]:
            if score >= 70:
                return "EXCELLENT"
            if score >= 40:
                return "GOOD"
            return "LOW"

        def _energy_intensity_factor(category: str, name: str) -> float:
            c = (category or "").lower()
            n = (name or "").lower()
            if "industr" in c or "fabbr" in c or "logistic" in c or "ingrosso" in c or "deposit" in c:
                return 1.0
            if "hotel" in c or "alberg" in c or "resort" in c:
                return 0.7
            if "uffic" in c or "studio" in c or "office" in c:
                return 0.3
            if "industr" in n or "fabbric" in n or "logistic" in n or "ingrosso" in n or "deposit" in n:
                return 1.0
            if "hotel" in n or "resort" in n or "alberg" in n:
                return 0.7
            return 0.5

        def _estimated_surface_m2(name: str, category: str) -> int:
            n = (name or "").lower()
            c = (category or "").lower()
            has_spa = ("s.p.a" in n) or (" spa" in n)
            is_industrial = (
                "industr" in n
                or "fabbric" in n
                or "logistic" in n
                or "ingrosso" in n
                or "deposit" in n
                or "magazz" in n
                or "industr" in c
                or "logistic" in c
            )
            if has_spa and is_industrial:
                return 2000
            if is_industrial:
                return 1400
            if "hotel" in n or "resort" in n or "alberg" in n or "hotel" in c:
                return 900
            if "centro" in n or "supermerc" in n or "market" in n:
                return 1200
            return 400

        def _yield_kwh_per_kwp(city: str) -> int:
            c = (city or "").strip().lower()
            known = {
                "milano": 1100,
                "torino": 1120,
                "bologna": 1200,
                "firenze": 1250,
                "roma": 1300,
                "napoli": 1400,
                "bari": 1420,
                "palermo": 1450,
                "catania": 1450,
                "cagliari": 1420,
            }
            if c in known:
                return known[c]
            if _is_south_city(city):
                return 1400
            return 1150

        def _compute_scientific_case(name: str, category: str, city: str, solar_score: int) -> Dict[str, Any]:
            area_m2 = int(_estimated_surface_m2(name, category))
            intensity = float(_energy_intensity_factor(category, name))

            # Simple PV sizing heuristic: ~1 kWp per 5.5 m2 => 0.18 kWp/m2
            kwp = int(round(max(5.0, area_m2 * 0.18)))

            # Use intensity as proxy for self-consumption / value of energy (bigger load => more value)
            yield_kwh_kwp = int(_yield_kwh_per_kwp(city))
            annual_kwh = int(round(kwp * yield_kwh_kwp))

            # CO2 avoided (t/yr): use 0.35 kgCO2/kWh as conservative grid factor
            annual_co2_tons = round((annual_kwh * 0.35) / 1000.0, 1)

            # Simple economics: CAPEX 950 €/kWp, value of self-consumed kWh 0.22 €/kWh
            capex = kwp * 950
            annual_savings = int(round(annual_kwh * 0.22 * min(1.0, max(0.45, intensity))))
            payback = None
            if annual_savings > 0:
                payback = round(capex / float(annual_savings), 1)
                payback = max(1.8, min(9.0, payback))

            years_txt = "—" if payback is None else str(int(round(payback)))
            business_case = f"Ritorno in {years_txt} anni"

            has_spa = ("s.p.a" in (name or "").lower()) or (" spa" in (name or "").lower())
            diamond = bool(has_spa and _is_south_city(city))

            msg = (
                f"Buongiorno {name}, abbiamo analizzato il vostro tetto e stimato un impianto da {kwp} kWp "
                f"con produzione annua ~{annual_kwh:,} kWh. Risparmio stimato ~{annual_savings:,} €/anno. "
                f"Se vi interessa, possiamo inviare una proposta tecnica e un sopralluogo." 
            ).replace(",", ".")

            # Make sure top leads look premium: if solar_score is extremely high, cap payback label to 3-4 anni
            if solar_score >= 95 and payback is not None and payback > 4.0:
                business_case = "Ritorno in 4 anni"

            return {
                "estimated_area_m2": area_m2,
                "estimated_kwp": kwp,
                "annual_kwh": annual_kwh,
                "annual_co2_tons": annual_co2_tons,
                "annual_savings_eur": annual_savings,
                "payback_years": payback,
                "business_case": business_case,
                "diamond_target": diamond,
                "whatsapp_message": msg,
            }

        def _stable_bucket_value(name: str) -> float:
            h = hashlib.sha256((name or "").encode("utf-8", errors="ignore")).hexdigest()
            # 0..1
            return int(h[:8], 16) / float(0xFFFFFFFF)

        def _kwp_from_roof_type(roof_type: str, name: str) -> int:
            r = (roof_type or "").lower()
            v = _stable_bucket_value(name)
            if "capannone" in r:
                lo, hi = 150, 400
            elif "commerci" in r:
                lo, hi = 40, 80
            else:
                lo, hi = 6, 12
            return int(round(lo + (hi - lo) * v))

        def _roi_label(city: str) -> str:
            return "RITORNO IN 3 ANNI" if _is_south_city(city) else "RITORNO IN 5 ANNI"

        async def _fetch_contact_page(base_url: str) -> str:
            try:
                parsed = urllib.parse.urlparse(base_url)
                root = f"{parsed.scheme}://{parsed.netloc}"
            except Exception:
                return ""

            paths = ("/contatti", "/contatto", "/contact", "/contacts")
            headers = {"User-Agent": "Mozilla/5.0"}
            for p in paths:
                try:
                    async with httpx.AsyncClient(follow_redirects=True, timeout=8.0, headers=headers) as client:
                        r = await client.get(root + p)
                        if r.status_code < 400 and (r.text or "").strip():
                            return r.text
                except Exception:
                    continue
            return ""

        for i, item in enumerate(raw):
            name = item.get("business_name") or "Unknown"
            website = item.get("website")
            website_norm = normalize_website(website) if website else None

            lat = item.get("lat")
            lon = item.get("lon")
            try:
                lat = None if lat is None else float(lat)
            except Exception:
                lat = None
            try:
                lon = None if lon is None else float(lon)
            except Exception:
                lon = None

            website_http_status: Optional[int] = None
            website_error: Optional[str] = None
            website_error_line: Optional[int] = None
            website_error_hint: Optional[str] = None
            website_html: Optional[str] = None
            website_has_html = False
            tech_stack = "Custom HTML"
            load_speed_s: Optional[float] = None
            domain_creation_date: Optional[str] = None
            domain_expiration_date: Optional[str] = None

            if website_norm:
                await job.emit(
                    12 + int((i / total) * 80),
                    f"Analizzando sito web di {name}...",
                )
                try:
                    (
                        audit,
                        tech_stack,
                        load_speed_s,
                        domain_creation_date,
                        domain_expiration_date,
                        email,
                        website_http_status,
                        website_error,
                        website_html,
                        website_error_line,
                        website_error_hint,
                    ) = await asyncio.wait_for(audit_website_with_status(website_norm), timeout=25.0)
                except asyncio.TimeoutError:
                    audit, email = AuditSignals(), None
                    tech_stack = "Custom HTML"
                    load_speed_s = None
                    domain_creation_date = None
                    domain_expiration_date = None
                    website_http_status, website_error = None, "Timeout"
                    website_error_line, website_error_hint = None, "Timeout"

                if (not email) and website_html:
                    try:
                        email = extract_email_from_html(website_html)
                    except Exception:
                        pass
                website_status: Literal["HAS_WEBSITE", "MISSING_WEBSITE"] = "HAS_WEBSITE"
            else:
                audit = AuditSignals()
                email = None
                tech_stack = "Custom HTML"
                load_speed_s = None
                domain_creation_date = None
                domain_expiration_date = None
                website_status = "MISSING_WEBSITE"

            if website_html:
                try:
                    # Cap to avoid huge memory usage (HTML can be very large)
                    job.site_html[i] = website_html[:200000]
                    website_has_html = True
                except Exception:
                    pass

            solar_score = _compute_solar_score(name, job.city, website_html)
            solar_bucket = _bucket(solar_score)
            roof = _roof_type(name)
            try:
                # kWp dynamic by roof type (no two rows identical)
                kwp_dynamic = _kwp_from_roof_type(roof, name)
            except Exception:
                kwp_dynamic = 80

            estimate = f"STIMA: {kwp_dynamic} kWp"

            try:
                scientific = _compute_scientific_case(name, job.category, job.city, solar_score)
            except Exception:
                scientific = {
                    "estimated_area_m2": None,
                    "estimated_kwp": kwp_dynamic,
                    "annual_kwh": None,
                    "annual_co2_tons": None,
                    "annual_savings_eur": None,
                    "payback_years": None,
                    "business_case": None,
                    "diamond_target": False,
                    "whatsapp_message": None,
                }

            try:
                yield_kwh_kwp = _yield_kwh_per_kwp(job.city)
            except Exception:
                yield_kwh_kwp = 1200

            try:
                annual_kwh = int(round(float(kwp_dynamic) * float(yield_kwh_kwp)))
            except Exception:
                annual_kwh = None

            annual_co2_tons = None
            annual_savings_eur = None
            try:
                if annual_kwh is not None:
                    annual_co2_tons = round((annual_kwh * 0.35) / 1000.0, 1)
                    annual_savings_eur = int(round(annual_kwh * 0.22))
            except Exception:
                annual_co2_tons = None
                annual_savings_eur = None

            scientific["estimated_kwp"] = kwp_dynamic
            scientific["annual_kwh"] = annual_kwh
            scientific["annual_co2_tons"] = annual_co2_tons
            scientific["annual_savings_eur"] = annual_savings_eur

            try:
                scientific["business_case"] = _roi_label(job.city)
                scientific["payback_years"] = 3.0 if _is_south_city(job.city) else 5.0
            except Exception:
                scientific["business_case"] = "RITORNO IN 5 ANNI"
                scientific["payback_years"] = 5.0

            # Deep contact scraping: search for mobile in homepage + contact page
            found_phone: Optional[str] = None
            if website_norm:
                try:
                    if website_html:
                        soup = BeautifulSoup(website_html, "html.parser")
                        found_phone = extract_phone_from_html(soup)
                    if not found_phone:
                        contact_html = await _fetch_contact_page(website_norm)
                        if contact_html:
                            soup = BeautifulSoup(contact_html, "html.parser")
                            found_phone = extract_phone_from_html(soup)
                except Exception:
                    found_phone = None

            final_phone = item.get("phone")
            if found_phone:
                final_phone = found_phone

            final_phone, _is_mobile = clean_phone(final_phone)

            results.append(
                BusinessResult(
                    result_index=i,
                    business_name=name,
                    address=item.get("address"),
                    lat=lat,
                    lon=lon,
                    phone=final_phone,
                    email=email,
                    website=website_norm,
                    website_status=website_status,
                    tech_stack=tech_stack,
                    load_speed_s=load_speed_s,
                    load_speed=None if load_speed_s is None else round(float(load_speed_s), 2),
                    domain_creation_date=domain_creation_date,
                    domain_expiration_date=domain_expiration_date,
                    website_http_status=website_http_status,
                    website_error=website_error,
                    website_has_html=website_has_html,
                    website_error_line=website_error_line,
                    website_error_hint=website_error_hint,
                    instagram_missing=bool(getattr(audit, "missing_instagram", False)),
                    tiktok_missing=not bool(getattr(audit, "has_tiktok_pixel", False)),
                    pixel_missing=not bool(getattr(audit, "has_facebook_pixel", False)),
                    solar_score=solar_score,
                    solar_potential_bucket=solar_bucket,
                    roof_type=roof,
                    plant_estimate=estimate,
                    estimated_area_m2=scientific.get("estimated_area_m2"),
                    estimated_kwp=scientific.get("estimated_kwp"),
                    annual_kwh=scientific.get("annual_kwh"),
                    annual_co2_tons=scientific.get("annual_co2_tons"),
                    annual_savings_eur=scientific.get("annual_savings_eur"),
                    payback_years=scientific.get("payback_years"),
                    business_case=scientific.get("business_case"),
                    diamond_target=scientific.get("diamond_target"),
                    whatsapp_message=scientific.get("whatsapp_message"),
                    audit=audit,
                )
            )

            # Persist lead to history immediately after completing its audit.
            try:
                lead_id = item.get("lead_id")
                if not lead_id:
                    lead_id = _make_lead_id(name, item.get("address"), item.get("phone"))
                _append_lead_history(str(lead_id))
            except Exception:
                pass

            # Stream partial results so the UI can update in real-time.
            job.results = list(results)
            try:
                await job.emit(
                    12 + int(((i + 1) / total) * 80),
                    f"Audit in corso: {i + 1}/{len(raw)}",
                )
            except Exception:
                pass

        job.results = results
        job.state = "done"
        job.finished_at = time.time()
        await job.emit(100, "Audit completato. Risultati pronti.")
    except Exception as e:
        job.state = "error"
        job.finished_at = time.time()
        job.error = str(e)
        print("JOB ERROR:", job.error)
        print(traceback.format_exc())
        await job.emit(100, f"Errore: {job.error}")


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/scrape")
async def scrape_endpoint(payload: StartJobRequest, background: BackgroundTasks):
    try:
        return await start_job(payload, background)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"ok": False, "error": e.detail})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@app.post("/jobs", response_model=JobStatus)
async def start_job(payload: StartJobRequest, background: BackgroundTasks) -> JobStatus:
    if _demo_cities:
        if payload.city.strip() not in _demo_cities:
            raise HTTPException(
                status_code=400,
                detail=f"DEMO: città consentite: {', '.join(_demo_cities)}",
            )
    if _demo_categories:
        if payload.category.strip() not in _demo_categories:
            raise HTTPException(
                status_code=400,
                detail=f"DEMO: categorie consentite: {', '.join(_demo_categories)}",
            )

    job_id = str(uuid.uuid4())
    job = Job(id=job_id, category=payload.category, city=payload.city, zone=payload.zone)
    JOBS[job_id] = job
    background.add_task(run_job, job)

    return JobStatus(
        id=job.id,
        state=job.state,
        progress=job.progress,
        message=job.message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
    )


@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job(job_id: str) -> JobStatus:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        id=job.id,
        state=job.state,
        progress=job.progress,
        message=job.message,
        started_at=job.started_at,
        finished_at=job.finished_at,
        error=job.error,
        results_count=len(job.results),
    )


@app.get("/jobs/{job_id}/results", response_model=List[BusinessResult])
async def get_results(job_id: str) -> List[BusinessResult]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.results


@app.get("/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def gen() -> AsyncGenerator[bytes, None]:
        yield b"retry: 1000\n\n"
        # Send an initial snapshot immediately.
        init_payload = json.dumps(
            {
                "progress": job.progress,
                "message": job.message,
                "state": job.state,
                "error": job.error,
                "results_count": len(job.results),
            },
            ensure_ascii=False,
        )
        yield f"data: {init_payload}\n\n".encode("utf-8")
        while True:
            try:
                event = await asyncio.wait_for(job.events.get(), timeout=10.0)
            except asyncio.TimeoutError:
                # Keep-alive comment line (SSE clients ignore it)
                yield b": keep-alive\n\n"
                continue
            payload = json.dumps(event, ensure_ascii=False)
            data = f"data: {payload}\n\n"
            yield data.encode("utf-8")
            if job.state in {"done", "error"} and job.progress >= 100:
                break

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/jobs/{job_id}/export.csv")
async def export_csv(job_id: str) -> Response:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    def _normalize_phone_digits(phone: Optional[str]) -> str:
        raw = (phone or "").strip()
        if not raw:
            return ""
        v = raw
        v = v.replace(" ", "")
        v = v.replace("-", "")
        v = v.replace("(", "")
        v = v.replace(")", "")
        if v.startswith("+39"):
            v = v[3:]
        if v.startswith("0039"):
            v = v[4:]
        v = re.sub(r"\D+", "", v)
        return v

    def _format_phone(phone: Optional[str]) -> str:
        digits, is_mobile = clean_phone(phone)
        if not digits:
            return ""
        if is_mobile:
            return "📱 " + digits
        return "☎️ " + digits

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "NOME AZIENDA",
            "TELEFONO",
            "INDIRIZZO",
            "CATEGORIA",
            "EMAIL",
        ]
    )

    def _sort_key(r: BusinessResult) -> Tuple[int, int]:
        phone_out = _format_phone(getattr(r, "phone", None))
        pri = 0 if phone_out.startswith("📱 ") else 1
        return (pri, int(getattr(r, "result_index", 0) or 0))

    for r in sorted(list(job.results), key=_sort_key):
        phone_out = _format_phone(getattr(r, "phone", None))
        if not phone_out:
            continue
        writer.writerow(
            [
                r.business_name,
                phone_out,
                r.address or "",
                getattr(job, "category", "") or "",
                r.email or "",
            ]
        )

    data = output.getvalue().encode("utf-8")
    filename = f"audit_{job.category}_{job.city}.csv".replace(" ", "_")

    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/jobs/{job_id}/sites/{result_index}/html")
async def view_site_html(job_id: str, result_index: int, line: Optional[int] = None) -> Response:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    src = job.site_html.get(result_index)
    if not src:
        raise HTTPException(status_code=404, detail="HTML not available for this result")

    lines = src.splitlines()
    highlight = None
    try:
        if line is not None and int(line) > 0:
            highlight = int(line)
    except Exception:
        highlight = None

    out: List[str] = []
    out.append("<html><head><meta charset='utf-8'>")
    out.append("<title>HTML View</title>")
    out.append(
        "<style>body{font-family:ui-monospace,Consolas,monospace;background:#0b0b0c;color:#eaeaea;}"
        ".wrap{max-width:1200px;margin:24px auto;padding:0 16px;}"
        ".line{white-space:pre-wrap;word-break:break-word;border-bottom:1px solid #1b1b1c;padding:2px 0;}"
        ".n{display:inline-block;width:64px;color:#8a8a8a;}"
        ".hl{background:rgba(255,0,0,0.12);}"
        "a{color:#9bd;}"
        "</style>"
    )
    out.append("</head><body><div class='wrap'>")
    if highlight:
        out.append(f"<div style='margin-bottom:12px'>Highlight line: <a href='#L{highlight}'>L{highlight}</a></div>")
    for i, l in enumerate(lines, start=1):
        cls = "line hl" if highlight == i else "line"
        out.append(
            f"<div id='L{i}' class='{cls}'><span class='n'>{i:>6}</span>{_html.escape(l)}</div>"
        )
    out.append("</div></body></html>")

    return Response(content="\n".join(out).encode("utf-8"), media_type="text/html")


@app.get("/jobs/{job_id}/results/{result_index}/technical-audit")
async def technical_audit(job_id: str, result_index: int) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        idx = int(result_index)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid result_index")

    if idx in job.technical_audits:
        return job.technical_audits[idx]

    if idx < 0 or idx >= len(job.results):
        raise HTTPException(status_code=404, detail="Result not found")

    row = job.results[idx]
    if row.website_status != "HAS_WEBSITE" or not row.website:
        raise HTTPException(status_code=400, detail="No website to audit")

    try:
        report = await asyncio.to_thread(run_technical_audit, row.website)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Technical audit failed: {str(e)}")

    job.technical_audits[idx] = report
    return report


@app.get("/jobs/{job_id}/results/{result_index}/solar-analysis")
async def solar_analysis(job_id: str, result_index: int) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    idx = int(result_index)
    if idx < 0 or idx >= len(job.results):
        raise HTTPException(status_code=404, detail="Result not found")
    
    row = job.results[idx]
    
    if row.lat is None or row.lon is None:
        raise HTTPException(
            status_code=400,
            detail="Coordinate non disponibili per questo lead"
        )
    
    # Cache sul job
    cache_key = f"solar_{idx}"
    if hasattr(job, "_solar_cache") and cache_key in job._solar_cache:
        return job._solar_cache[cache_key]
    
    try:
        result = await fetch_solar_analysis(row.lat, row.lon)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    
    if not hasattr(job, "_solar_cache"):
        job._solar_cache = {}
    job._solar_cache[cache_key] = result
    return result


@app.get("/jobs/{job_id}/results/{result_index}/report.pdf")
async def download_pdf_report(job_id: str, result_index: int) -> Response:
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    try:
        idx = int(result_index)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid result_index")

    if idx < 0 or idx >= len(job.results):
        raise HTTPException(status_code=404, detail="Result not found")

    row = job.results[idx]
    issues: List[Dict[str, Any]] = []
    if row.website_status == "HAS_WEBSITE" and row.website:
        cached = job.technical_audits.get(idx)
        if cached is None:
            try:
                cached = await asyncio.to_thread(run_technical_audit, row.website)
                job.technical_audits[idx] = cached
            except Exception:
                cached = None
        if cached and isinstance(cached.get("issues"), list):
            issues = cached["issues"]

    try:
        pdf_bytes = await asyncio.to_thread(
            generate_audit_pdf,
            business_name=row.business_name,
            phone=row.phone,
            issues=issues,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"AUDIT_{row.business_name}".replace(" ", "_")
    filename = re.sub(r"[^a-zA-Z0-9_\-]", "", filename)[:60] or "AUDIT"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
    )


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    if not _HAS_FRONTEND_OUT:
        raise HTTPException(status_code=404, detail="Frontend not built")

    rel = (full_path or "").lstrip("/")
    p = os.path.join(_FRONTEND_OUT_DIR, rel)

    if rel and os.path.isfile(p):
        return FileResponse(p)

    if rel and os.path.isdir(p):
        idx = os.path.join(p, "index.html")
        if os.path.isfile(idx):
            return FileResponse(idx)

    return FileResponse(os.path.join(_FRONTEND_OUT_DIR, "index.html"))


if __name__ == "__main__":
    import uvicorn
    import threading
    import webbrowser

    # FULL executable hardening: ignore any DEMO_* env vars that may be set
    # in the user's environment, to avoid unintended result caps.
    try:
        os.environ.pop("DEMO_CITY", None)
        os.environ.pop("DEMO_CATEGORIES", None)
        os.environ.pop("DEMO_MAX_RESULTS", None)
    except Exception:
        pass

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8010"))

    ui_url = f"http://127.0.0.1:{port}"
    print(f"ClientSniper running on {ui_url}")

    def _is_port_listening(h: str, p: int) -> bool:
        try:
            with socket.create_connection((h, p), timeout=0.25):
                return True
        except OSError:
            return False

    # If another instance is already running on the fixed port, just open the UI.
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
