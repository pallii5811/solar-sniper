import asyncio, json, re, uuid, time, io
import threading
import webbrowser
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Literal, Optional, Tuple
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, Response
from fastapi.middleware.cors import CORSMiddleware
try: from playwright.sync_api import sync_playwright
except: sync_playwright = None
try: from openpyxl import Workbook
except: Workbook = None


CATEGORIES = ["Grossisti", "Centri Sportivi", "Celle Frigorifere", "Fabbriche", "Logistica"]


@dataclass
class Job:
    id: str
    category: str
    city: str = "Milano"
    state: str = "queued"
    progress: int = 0
    message: str = "In coda"
    results: list = field(default_factory=list)
    events: asyncio.Queue = field(default_factory=asyncio.Queue)

    async def emit(self, p, m):
        self.progress = p
        self.message = m
        await self.events.put({"progress": p, "message": m, "state": self.state})


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: Dict[str, Job] = {}


def scrape_logic(category: str, city: str) -> List[Dict[str, Any]]:
    if not sync_playwright:
        return []

    results: List[Dict[str, Any]] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        q = f"{category} {city}".strip()
        page.goto(
            f"https://www.google.it/maps/search/{q}",
            timeout=90_000,
            wait_until="domcontentloaded",
        )

        # --- FIX COOKIE ---
        try:
            # Aspetta che appaia uno dei tasti e cliccalo
            page.wait_for_selector("button", timeout=3000)
            if page.locator("#L2AGLb").is_visible(): 
                page.locator("#L2AGLb").click()
            elif page.locator("button[aria-label='Accetta tutto']").is_visible():
                page.locator("button[aria-label='Accetta tutto']").click()
            elif page.locator("button:has-text('Accetta tutto')").is_visible():
                page.locator("button:has-text('Accetta tutto')").click()
        except: 
            pass
        page.wait_for_timeout(2000)
        # ------------------
        try:
            page.click("button[aria-label='Accetta tutto']", timeout=5000)
        except Exception:
            pass

        page.wait_for_timeout(3000)

        cards = page.locator('div[role="article"]').all()
        for card in cards[:5]:
            try:
                card.click()
                page.wait_for_timeout(2500)

                url = page.url
                coords = re.search(r'@(-?[\d\.]+),(-?[\d\.]+)', url)

                name = ""
                try:
                    name = page.locator("h1.DUwDvf").inner_text(timeout=3000).strip()
                except Exception:
                    name = ""

                phone = ""
                try:
                    phone_loc = page.locator('button[data-item-id^="phone:"]')
                    if phone_loc.count() > 0:
                        phone = phone_loc.first.inner_text(timeout=2000).strip()
                except Exception:
                    phone = ""

                if not phone:
                    continue

                roof = ""
                if coords:
                    lat, lng = coords.groups()
                    # Link a Google Earth con Pin esatto e visuale 3D sul tetto
                    roof = f"https://earth.google.com/web/search/{lat},{lng}/@{lat},{lng},100a,35y,0h,0t,0r"

                results.append({"name": name, "phone": phone, "roof": roof})
            except Exception:
                continue

        browser.close()

    return results


async def run_job(job: Job) -> None:
    job.state = "running"
    await job.emit(10, "Avvio Solar Sniper...")

    try:
        job.results = await asyncio.to_thread(scrape_logic, job.category, "Milano")
        job.state = "done"
        await job.emit(100, "Analisi Tetto completata!")
    except Exception as e:
        job.state = "error"
        await job.emit(100, f"Errore: {e}")


@app.post("/jobs")
async def start(data: Dict[str, Any], bg: BackgroundTasks) -> Dict[str, str]:
    category = (data or {}).get("category")
    if not isinstance(category, str):
        raise HTTPException(400, "Settore non abilitato")
    category = category.strip()
    if category not in CATEGORIES:
        raise HTTPException(400, "Settore non abilitato")

    jid = str(uuid.uuid4())
    job = Job(id=jid, category=category)
    JOBS[jid] = job
    bg.add_task(run_job, job)
    return {"id": jid}


@app.get("/jobs/{jid}/events")
async def events(jid: str) -> StreamingResponse:
    job = JOBS[jid]

    async def gen() -> AsyncGenerator[bytes, None]:
        while True:
            evt = await job.events.get()
            yield f"data: {json.dumps(evt)}\n\n".encode("utf-8")
            if job.state in ["done", "error"]:
                break

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/jobs/{jid}/results")
async def results(jid: str) -> List[Dict[str, Any]]:
    return JOBS[jid].results


_HTML = """
<!doctype html>
<html lang="it">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Solar Sniper</title>
  <style>
    body { font-family: Arial, sans-serif; background:#0b0f14; color:#e5e7eb; margin:0; }
    .wrap { max-width: 920px; margin: 0 auto; padding: 22px; }
    .card { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 16px; }
    label { font-size: 12px; color:#a1a1aa; display:block; margin-bottom: 6px; }
    select,input { height: 44px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.12); background: transparent; color:#e5e7eb; padding: 0 12px; }
    button { height: 44px; border-radius: 12px; border: 0; background:#00e676; color:#0b0f14; font-weight: 800; padding: 0 16px; cursor:pointer; }
    button:disabled { opacity: 0.5; cursor:not-allowed; }
    table { width:100%; border-collapse: collapse; margin-top: 16px; }
    th,td { text-align:left; border-bottom: 1px solid rgba(255,255,255,0.08); padding: 10px 6px; font-size: 14px; }
    a { color:#00e676; text-decoration:none; }
    .title { font-size: 28px; font-weight: 900; letter-spacing: 0.5px; }
    .muted { color:#a1a1aa; font-size: 13px; }
    .row { display:flex; gap: 12px; flex-wrap: wrap; align-items:end; }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="title">Solar Sniper</div>
    <div class="muted" style="margin-top:6px">Lead Fotovoltaico - Analisi Tetto</div>

    <div class="card" style="margin-top:16px">
      <div class="row">
        <div>
          <label>Settore</label>
          <select id="cat">
            <option value="Grossisti">Grossisti</option>
            <option value="Centri Sportivi">Centri Sportivi</option>
            <option value="Celle Frigorifere">Celle Frigorifere</option>
            <option value="Fabbriche">Fabbriche</option>
            <option value="Logistica">Logistica</option>
          </select>
        </div>
        <div>
          <label>Città</label>
          <input id="city" value="Milano" readonly />
        </div>
        <div>
          <button id="start">Avvia Analisi Tetto</button>
        </div>
        <div class="muted" id="status"></div>
      </div>

      <table>
        <thead>
          <tr>
            <th>Lead Fotovoltaico</th>
            <th>Telefono</th>
            <th>Analisi Tetto</th>
          </tr>
        </thead>
        <tbody id="rows"></tbody>
      </table>
    </div>
  </div>

<script>
  const startBtn = document.getElementById('start');
  const statusEl = document.getElementById('status');
  const rowsEl = document.getElementById('rows');
  const catEl = document.getElementById('cat');

  function setStatus(t) { statusEl.textContent = t || ''; }
  function renderRows(items) {
    rowsEl.innerHTML = '';
    for (const it of (items || [])) {
      const tr = document.createElement('tr');
      const name = document.createElement('td');
      name.textContent = it.name || '';
      const phone = document.createElement('td');
      phone.textContent = it.phone || '';
      const roof = document.createElement('td');
      if (it.roof) {
        const a = document.createElement('a');
        a.href = it.roof;
        a.target = '_blank';
        a.rel = 'noreferrer';
        a.textContent = 'Apri';
        roof.appendChild(a);
      } else {
        roof.textContent = '—';
      }
      tr.appendChild(name);
      tr.appendChild(phone);
      tr.appendChild(roof);
      rowsEl.appendChild(tr);
    }
  }

  async function fetchJson(url, opts) {
    const r = await fetch(url, opts);
    if (!r.ok) {
      const t = await r.text();
      throw new Error(t || ('HTTP ' + r.status));
    }
    return await r.json();
  }

  startBtn.addEventListener('click', async () => {
    startBtn.disabled = true;
    rowsEl.innerHTML = '';
    setStatus('Avvio Solar Sniper...');
    try {
      const category = catEl.value;
      const job = await fetchJson('/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category })
      });
      const jid = job.id;
      const ev = new EventSource(`/jobs/${jid}/events`);
      ev.onmessage = async (e) => {
        try {
          const s = JSON.parse(e.data);
          setStatus((s.progress ?? 0) + '% - ' + (s.message || ''));
          if (s.state === 'done') {
            ev.close();
            const res = await fetchJson(`/jobs/${jid}/results`);
            renderRows(res);
            startBtn.disabled = false;
          }
          if (s.state === 'error') {
            ev.close();
            setStatus('Errore: ' + (s.message || 'Errore'));
            startBtn.disabled = false;
          }
        } catch {}
      };
      ev.onerror = () => {
        ev.close();
        setStatus('Errore');
        startBtn.disabled = false;
      };
    } catch (err) {
      setStatus('Errore');
      startBtn.disabled = false;
    }
  });
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return _HTML


if __name__ == "__main__":
    import uvicorn
    def _open():
        try:
            time.sleep(1.2)
            webbrowser.open("http://127.0.0.1:8010/")
        except Exception:
            pass

    try:
        threading.Thread(target=_open, daemon=True).start()
    except Exception:
        pass
    uvicorn.run(app, host="127.0.0.1", port=8010)
