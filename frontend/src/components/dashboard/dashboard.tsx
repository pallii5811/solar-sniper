"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown,
  ArrowUp,
  ExternalLink,
  FileDown,
  MessageCircle,
  Phone,
  Search,
  Rocket,
} from "lucide-react";
import * as React from "react";

import type { BusinessResult, JobStatus, TechnicalAuditResult } from "@/lib/api";
import {
  BACKEND_URL,
  fetchJob,
  fetchResults,
  fetchTechnicalAudit,
  startJob,
} from "@/lib/api";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const zone_database: Record<string, string[]> = {
  Milano: [
    "Tutta la città",
    "Centro Storico",
    "Brera",
    "Porta Nuova",
    "Isola",
    "CityLife",
    "Navigli",
    "Porta Romana",
    "Porta Venezia",
    "Lambrate",
    "NoLo",
    "Bicocca",
    "San Siro",
    "Città Studi",
    "Ticinese",
    "Sempione",
  ],
  Roma: [
    "Tutta la città",
    "Centro Storico",
    "Trastevere",
    "Prati",
    "Parioli",
    "EUR",
    "Testaccio",
    "San Lorenzo",
    "Pigneto",
    "Garbatella",
    "Monteverde",
    "Flaminio",
    "Ostiense",
    "Monti",
    "Trieste",
    "Nomentano",
  ],
  Torino: [
    "Tutta la città",
    "Centro",
    "Crocetta",
    "San Salvario",
    "Vanchiglia",
    "Cit Turin",
    "Santa Rita",
    "Lingotto",
    "Gran Madre",
    "Aurora",
    "San Paolo",
  ],
  Napoli: [
    "Tutta la città",
    "Chiaia",
    "Vomero",
    "Posillipo",
    "Centro Storico",
    "Rione Sanità",
    "Fuorigrotta",
    "Arenella",
    "San Ferdinando",
    "Porto",
  ],
  Bologna: [
    "Tutta la città",
    "Centro Storico",
    "Bolognina",
    "Saragozza",
    "San Donato",
    "Murri",
    "Colli",
    "Santo Stefano",
    "Porto",
  ],
  Firenze: [
    "Tutta la città",
    "Centro Storico",
    "Oltrarno",
    "Campo di Marte",
    "Rifredi",
    "Novoli",
    "Santa Croce",
    "Santo Spirito",
  ],
  Genova: [
    "Tutta la città",
    "Centro",
    "Porto Antico",
    "Albaro",
    "Castelletto",
    "Nervi",
    "Pegli",
    "Sampierdarena",
    "Foce",
  ],
  Venezia: [
    "Tutta la città",
    "San Marco",
    "Cannaregio",
    "Castello",
    "Dorsoduro",
    "Santa Croce",
    "San Polo",
    "Giudecca",
    "Mestre Centro",
    "Lido",
  ],
  Verona: [
    "Tutta la città",
    "Centro Storico",
    "Borgo Trento",
    "Borgo Venezia",
    "Borgo Roma",
    "San Zeno",
    "Veronetta",
  ],
  Bari: [
    "Tutta la città",
    "Bari Vecchia",
    "Murat",
    "Poggiofranco",
    "Carrassi",
    "San Pasquale",
    "Madonnella",
  ],
  Palermo: [
    "Tutta la città",
    "Centro Storico",
    "Politeama",
    "Libertà",
    "Kalsa",
    "Mondello",
    "Zisa",
  ],
  Catania: [
    "Tutta la città",
    "Centro Storico",
    "Corso Italia",
    "Lungomare",
    "Borgo-Sanzio",
    "Cibali",
  ],
  Padova: ["Tutta la città", "Centro", "Arcella", "Guizza", "Portello", "Stanga", "Santa Croce"],
  Trieste: [
    "Tutta la città",
    "Borgo Teresiano",
    "San Giusto",
    "Barcola",
    "Roiano",
    "Città Vecchia",
  ],
  Brescia: [
    "Tutta la città",
    "Centro Storico",
    "Brescia Due",
    "Mompiano",
    "Lamarmora",
    "Borgo Trento",
  ],
  Bergamo: [
    "Tutta la città",
    "Città Alta",
    "Città Bassa",
    "Borgo Palazzo",
    "Redona",
    "Loreto",
  ],
  Salerno: [
    "Tutta la città",
    "Centro Storico",
    "Lungomare",
    "Pastena",
    "Torrione",
    "Carmine",
  ],
  Monza: ["Tutta la città", "Centro", "Parco", "San Biagio", "Triante", "San Fruttuoso"],
  Parma: ["Tutta la città", "Centro Storico", "Oltretorrente", "Cittadella", "San Lazzaro"],
  Modena: ["Tutta la città", "Centro Storico", "Crocetta", "Buon Pastore", "San Faustino"],
};

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

function buildPitchEmail(row: BusinessResult) {
  const name = row.business_name;

  if (row.website_status === "MISSING_WEBSITE") {
    return {
      subject: `Solar Sniper — opportunità FV per ${name} (stima rapida)`,
      body:
        `Ciao ${name},\n\n` +
        `ho analizzato rapidamente la tua attività con Solar Sniper: stima consumi e potenziale fotovoltaico, più i contatti principali disponibili (telefono/email).\n\n` +
        `Se ti va, ti invio una scheda sintetica con: stima kWp, risparmio annuo indicativo e link satellitare dell'area.\n\n` +
        `Ti interessa riceverla?\n\n` +
        `—`,
    };
  }

  if (row.website_status === "HAS_WEBSITE" && !row.audit.has_facebook_pixel) {
    return {
      subject: `Solar Sniper — analisi rapida FV per ${name}`,
      body:
        `Ciao ${name},\n\n` +
        `ho analizzato rapidamente la tua attività con Solar Sniper: stima consumi e potenziale fotovoltaico, più i contatti principali disponibili (telefono/email).\n\n` +
        `Se ti va, ti invio una scheda sintetica con: stima kWp, risparmio annuo indicativo e link satellitare dell'area.\n\n` +
        `Ti interessa riceverla?\n\n` +
        `—`,
    };
  }

  return {
    subject: `Solar Sniper — stima FV e contatti per ${name}`,
    body:
      `Ciao ${name},\n\n` +
      `ho analizzato rapidamente la tua attività con Solar Sniper: stima consumi e potenziale fotovoltaico, link satellitare e contatti disponibili (telefono/email).\n\n` +
      `Se ti va, ti invio una scheda sintetica con: stima kWp, risparmio annuo indicativo e link satellitare dell'area.\n\n` +
      `Ti interessa riceverla?\n\n` +
      `—`,
  };
}

function buildAuditIssues(row: BusinessResult): string[] {
  const issues: string[] = [];
  if (row.website_status === "MISSING_WEBSITE") {
    issues.push("Scheda: contatti da verificare");
    return issues;
  }

  if (!row.audit.has_facebook_pixel) issues.push("Scheda: opportunità FV");
  if (!row.audit.has_gtm) issues.push("Scheda: consumi stimati");
  if (!row.audit.has_ssl) issues.push("Scheda: link satellitare");
  if (!row.audit.is_mobile_responsive) issues.push("Scheda: contatti disponibili");
  return issues;
}

function cleanPhoneForWhatsApp(phone: string): string {
  let p = phone.trim();
  p = p.replace(/^\+/, "");
  p = p.replace(/^00/, "");
  p = p.replace(/[^0-9]/g, "");
  if (p.startsWith("39") && p.length > 10) return p;
  if (p.startsWith("3") && (p.length === 9 || p.length === 10)) return `39${p}`;
  if (p.startsWith("0") && p.length >= 9) return `39${p}`;
  return p;
}

function normalizePhoneForType(phone?: string | null): string {
  if (!phone) return "";
  let p = String(phone).trim();
  p = p.replace(/\s+/g, "");
  p = p.replace(/[-()]/g, "");
  // Keep digits only
  p = p.replace(/[^0-9]/g, "");
  if (p.startsWith("0039")) p = p.slice(4);
  if (p.startsWith("39") && p.length > 10) p = p.slice(2);
  return p;
}

function isMobilePhone(phone?: string | null): boolean {
  const p = normalizePhoneForType(phone);
  if (!p) return false;
  return /^3[2-9]\d{8}$/.test(p);
}

function isFixedPhone(phone?: string | null): boolean {
  const p = normalizePhoneForType(phone);
  if (!p) return false;
  return p.startsWith("0") && p.length >= 9;
}

function buildSocialSearchUrl(businessName: string, city: string): string {
  const q = `site:instagram.com OR site:facebook.com "${businessName} ${city}"`;
  return `https://www.google.com/search?q=${encodeURIComponent(q)}`;
}

function cleanCompanyName(businessName: string): string {
  const base = String(businessName || "").replace(/\s+/g, " ").trim();
  const cut = base.split(/\s*[-|]\s*/)[0] ?? base;
  return String(cut).replace(/\s+/g, " ").trim();
}

function buildLinkedInCeoSearchUrl(businessName: string): string {
  const cleanName = cleanCompanyName(businessName);
  const keywords = `${cleanName} AND (CEO OR Titolare OR Amministratore OR Founder)`;
  return `https://www.linkedin.com/search/results/people/?keywords=${encodeURIComponent(
    keywords,
  )}&origin=GLOBAL_SEARCH_HEADER`;
}

function buildGoogleOwnerSearchUrl(businessName: string): string {
  const cleanName = cleanCompanyName(businessName);
  const q = `"${cleanName}" titolare amministratore contatti`;
  return `https://www.google.com/search?q=${encodeURIComponent(q)}`;
}

function buildRoofSatelliteUrl(address: string): string {
  const q = String(address || "").trim();
  return `https://earth.google.com/web/search/${encodeURIComponent(q)}/`;
}

function buildRoofSatelliteUrlFromCoords(address: string, lat: number, lon: number): string {
  void address;
  const latStr = Number.isFinite(lat) ? String(lat) : "";
  const lonStr = Number.isFinite(lon) ? String(lon) : "";
  if (!latStr || !lonStr) return "#";
  return `https://earth.google.com/web/search/${latStr},${lonStr}/@${latStr},${lonStr},100a,35y,0h,0t,0r`;
}

function getSatelliteLink(company: any, fallbackCity: string): string {
  const latitude =
    typeof company?.latitude === "number"
      ? company.latitude
      : typeof company?.lat === "number"
        ? company.lat
        : null;
  const longitude =
    typeof company?.longitude === "number"
      ? company.longitude
      : typeof company?.lon === "number"
        ? company.lon
        : null;

  if (
    latitude !== null &&
    longitude !== null &&
    Number.isFinite(latitude) &&
    Number.isFinite(longitude) &&
    latitude !== 0 &&
    longitude !== 0
  ) {
    return buildRoofSatelliteUrlFromCoords("", latitude, longitude);
  }

  const rawAddress = String(company?.address ?? "").trim();
  const rawCity = String(company?.city ?? fallbackCity ?? "").trim();
  const fullAddress = `${rawAddress} ${rawCity}`.trim();
  if (!fullAddress) return "#";
  return `https://earth.google.com/web/search/${encodeURIComponent(fullAddress)}/`;
}

function computeRoofTypeFromName(name: string): "CAPANNONE" | "RESIDENZIALE" {
  const n = String(name || "").toLowerCase();
  if (n.includes(" srl") || n.includes("spa") || n.includes("industria")) {
    return "CAPANNONE";
  }
  return "RESIDENZIALE";
}

function computePotentialFromName(name: string): {
  tier: "ECCELLENTE" | "BUONO";
  scoreText: "98/100" | "75/100";
} {
  const n = String(name || "").toLowerCase();
  if (n.includes("hotel") || n.includes("logistica") || n.includes("fabbrica")) {
    return { tier: "ECCELLENTE", scoreText: "98/100" };
  }
  return { tier: "BUONO", scoreText: "75/100" };
}

function computePlantEstimate(tier: "ECCELLENTE" | "BUONO"): string {
  return tier === "ECCELLENTE" ? "> 100kW" : "20-50kW";
}

function ResultsSkeleton() {
  return (
    <div className="overflow-hidden rounded-lg border border-border">
      <div className="bg-muted/40 px-4 py-3 text-sm text-muted-foreground">
        Loading results...
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="grid grid-cols-12 gap-4 px-4 py-4">
            <div className="col-span-4 space-y-2">
              <div className="h-4 w-3/4 animate-pulse rounded bg-muted" />
              <div className="h-3 w-full animate-pulse rounded bg-muted/70" />
            </div>
            <div className="col-span-3 space-y-2">
              <div className="h-3 w-5/6 animate-pulse rounded bg-muted" />
              <div className="h-3 w-3/6 animate-pulse rounded bg-muted/70" />
            </div>
            <div className="col-span-3 space-y-2">
              <div className="h-6 w-4/6 animate-pulse rounded bg-muted" />
              <div className="h-6 w-3/6 animate-pulse rounded bg-muted/70" />
            </div>
            <div className="col-span-2 space-y-2">
              <div className="h-6 w-full animate-pulse rounded bg-muted" />
              <div className="h-6 w-5/6 animate-pulse rounded bg-muted/70" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function hasWebsite(row: BusinessResult): boolean {
  if (row.website_status !== "HAS_WEBSITE") return false;
  const w = (row.website || "").trim();
  return w.length > 0;
}

function parseIsoDate(value?: string | null): Date | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d;
}

function daysUntil(d: Date): number {
  const ms = d.getTime() - Date.now();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function yearsSince(d: Date): number {
  const ms = Date.now() - d.getTime();
  return ms / (1000 * 60 * 60 * 24 * 365.25);
}

function isExpiringSoon(expirationIso?: string | null): boolean {
  const d = parseIsoDate(expirationIso);
  if (!d) return false;
  const days = daysUntil(d);
  return days >= 0 && days < 30;
}

function isLegacyBrand(creationIso?: string | null): boolean {
  const d = parseIsoDate(creationIso);
  if (!d) return false;
  return yearsSince(d) >= 10;
}

function ResultsTable({
  rows,
  city,
  onTechnical,
  onSolar,
}: {
  rows: BusinessResult[];
  city: string;
  onTechnical: (row: BusinessResult) => void;
  onSolar: (row: BusinessResult) => void;
}) {
  return (
    <div className="results-table-container glass-panel w-full overflow-x-auto whitespace-nowrap pb-5">
      <table className="results-table w-full min-w-[1600px] text-sm">
        <thead className="bg-white/[0.02]">
          <tr className="text-left text-[11px] uppercase tracking-widest text-slate-400">
            <th className="px-5 py-4 font-medium">Business Name</th>
            <th className="px-5 py-4 font-medium">Contacts</th>
            <th className="px-5 py-4 font-medium">🕵️ INVESTIGAZIONE</th>
            <th className="px-5 py-4 font-medium">TIPO TETTO</th>
            <th className="px-5 py-4 font-medium">POTENZIALE</th>
            <th className="px-5 py-4 font-medium">BUSINESS CASE</th>
            <th className="px-5 py-4 font-medium">RISPARMIO CO2</th>
            <th className="px-5 py-4 font-medium">STIMA IMPIANTO</th>
            <th className="px-5 py-4 font-medium">Address</th>
            <th className="px-2 py-4 font-medium w-[120px]">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => {
            const isSiteDown =
              typeof row.website_http_status === "number" && row.website_http_status >= 400;
            const isCritical =
              row.website_status === "MISSING_WEBSITE" ||
              isSiteDown ||
              Boolean(String(row.website_error ?? "").trim());
            const isDiamond = Boolean(row.diamond_target);
            const isNeonDiamond =
              typeof row.solar_score === "number" &&
              row.solar_score > 90 &&
              String(row.roof_type || "").toLowerCase().includes("capannone");
            const rowClass = isCritical
              ? `row-hover-glow border-t border-white/5 bg-[rgba(239,68,68,0.10)] ${
                  isDiamond ? "diamond-row" : ""
                }`
              : `row-hover-glow border-t border-white/5 ${isDiamond ? "diamond-row" : ""} ${
                  isNeonDiamond ? "neon-diamond-row" : ""
                }`;

            return (
              <motion.tr
                key={`${row.business_name}-${idx}`}
                className={rowClass}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, delay: Math.min(idx * 0.03, 0.6) }}
              >
                <td className="px-5 py-5">
                  <div>
                    <div className="font-semibold">{row.business_name}</div>
                    <div className="mt-1 text-xs text-muted-foreground">{row.address ?? ""}</div>
                    {row.diamond_target ? (
                      <div className="mt-2">
                        <Badge
                          variant="custom"
                          className="border-yellow-400/50 bg-yellow-400/10 text-yellow-100"
                        >
                          💎 DIAMOND TARGET
                        </Badge>
                      </div>
                    ) : null}
                  </div>
                </td>

                <td className="px-5 py-5">
                  <div className="space-y-2">
                    <div className="flex items-center gap-3">
                      {row.phone ? (
                        <>
                          <a
                            className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground"
                            href={`tel:${row.phone}`}
                          >
                            <Phone className="h-4 w-4" />
                            <span className="text-xs">{row.phone}</span>
                          </a>

                          {isMobilePhone(row.phone) ? (
                            <span className="rounded-md border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold tracking-wide text-emerald-300">
                              MOBILE
                            </span>
                          ) : null}

                          {isFixedPhone(row.phone) ? (
                            <span className="rounded-md border border-slate-500/40 bg-slate-500/10 px-2 py-1 text-[10px] font-semibold tracking-wide text-slate-200">
                              FISSO
                            </span>
                          ) : null}

                          {isMobilePhone(row.phone) ? (
                            <a
                              className="inline-flex items-center text-muted-foreground hover:text-foreground"
                              href={`https://wa.me/${cleanPhoneForWhatsApp(row.phone)}`}
                              target="_blank"
                              rel="noreferrer"
                              title="WhatsApp"
                            >
                              <MessageCircle className="h-4 w-4" />
                            </a>
                          ) : null}

                          {isMobilePhone(row.phone) ? (
                            <button
                              type="button"
                              className="rounded-md border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-[10px] font-semibold tracking-wide text-emerald-100 shadow-[0_0_12px_rgba(34,197,94,0.22)] hover:bg-emerald-400/15"
                              onClick={() => {
                                const phone = cleanPhoneForWhatsApp(row.phone || "");
                                const text =
                                  row.whatsapp_message ||
                                  `Buongiorno ${row.business_name}, abbiamo analizzato il vostro tetto e stimato un risparmio di ${
                                    row.annual_savings_eur ?? "—"
                                  } Euro/anno. Possiamo inviare una proposta?`;
                                window.open(
                                  `https://wa.me/${phone}?text=${encodeURIComponent(text)}`,
                                  "_blank",
                                  "noopener,noreferrer",
                                );
                              }}
                              title="Invia proposta WhatsApp"
                            >
                              INVIA PROPOSTA WHATSAPP
                            </button>
                          ) : null}

                          <button
                            type="button"
                            className="inline-flex items-center text-muted-foreground hover:text-foreground"
                            onClick={() =>
                              window.open(
                                buildSocialSearchUrl(row.business_name, city),
                                "_blank",
                                "noopener,noreferrer",
                              )
                            }
                            title="Find Social"
                          >
                            <Search className="h-4 w-4" />
                          </button>
                        </>
                      ) : (
                        <span className="text-xs text-muted-foreground">No phone</span>
                      )}

                      {row.website ? (
                        <a
                          className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground"
                          href={row.website}
                          target="_blank"
                          rel="noreferrer"
                        >
                          <ExternalLink className="h-4 w-4" />
                          <span className="text-xs">Website</span>
                        </a>
                      ) : null}
                    </div>

                    {row.email ? (
                      <div className="text-xs text-muted-foreground">{row.email}</div>
                    ) : null}
                  </div>
                </td>

                <td className="px-5 py-5">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      className="rounded-full border border-sky-400/40 bg-sky-500/15 p-2 text-xs font-bold text-sky-100 shadow-[0_0_14px_rgba(56,189,248,0.20)] hover:bg-sky-500/25 hover:shadow-[0_0_18px_rgba(56,189,248,0.38)]"
                      onClick={() =>
                        window.open(
                          buildLinkedInCeoSearchUrl(row.business_name),
                          "_blank",
                          "noopener,noreferrer",
                        )
                      }
                      title="Cerca CEO su LinkedIn"
                    >
                      in
                    </button>
                    <button
                      type="button"
                      className="rounded-full border border-orange-400/40 bg-orange-500/15 p-2 text-xs font-bold text-orange-100 shadow-[0_0_14px_rgba(249,115,22,0.18)] hover:bg-orange-500/25 hover:shadow-[0_0_18px_rgba(249,115,22,0.34)]"
                      onClick={() =>
                        window.open(
                          buildGoogleOwnerSearchUrl(row.business_name),
                          "_blank",
                          "noopener,noreferrer",
                        )
                      }
                      title="Trova Titolare su Google"
                    >
                      G
                    </button>
                  </div>
                </td>

                <td className="px-5 py-5">
                  <Badge
                    variant="custom"
                    className="border-white/10 bg-white/[0.03] text-slate-200"
                  >
                    {row.roof_type || computeRoofTypeFromName(row.business_name)}
                  </Badge>
                </td>

                {(() => {
                  const score = typeof row.solar_score === "number" ? row.solar_score : null;
                  const fallback = computePotentialFromName(row.business_name);

                  const isExcellent = score !== null ? score > 90 : fallback.tier === "ECCELLENTE";
                  const isHigh = score !== null ? score > 70 && score <= 90 : false;
                  const label = isExcellent
                    ? "💎 ECCELLENTE"
                    : isHigh
                      ? "🔥 ALTO POTENZIALE"
                      : "⚡️ BUON TARGET";
                  const scoreText = score !== null ? `${Math.round(score)}/100` : fallback.scoreText;

                  const tdGlow =
                    score !== null && score > 90
                      ? "shadow-[0_0_15px_rgba(34,197,94,0.6)] font-bold"
                      : "";
                  const badgeCls = isExcellent
                    ? "border-emerald-300/70 bg-emerald-400/20 text-emerald-50 shadow-[0_0_20px_rgba(34,197,94,0.8)]"
                    : isHigh
                      ? "border-emerald-400/45 bg-emerald-500/12 text-emerald-100"
                      : "border-yellow-400/30 bg-yellow-400/10 text-yellow-100";

                  return (
                    <td className={`px-5 py-5 min-w-[240px] ${tdGlow}`}>
                      <Badge variant="custom" className={badgeCls}>
                        <span
                          className={
                            isExcellent ? "font-extrabold text-[rgba(0,230,118,1)]" : "font-bold"
                          }
                        >
                          {label}
                        </span>
                        <span className="ml-2 font-semibold">{scoreText}</span>
                      </Badge>
                    </td>
                  );
                })()}

                <td className="px-5 py-5">
                  <Badge variant="custom" className="border-white/10 bg-white/[0.03] text-slate-200">
                    {row.business_case || "Calcolo in corso..."}
                  </Badge>
                </td>

                <td className="px-5 py-5">
                  <Badge
                    variant="custom"
                    className="border-emerald-400/25 bg-emerald-400/10 text-emerald-100"
                  >
                    {typeof row.annual_co2_tons === "number"
                      ? `${row.annual_co2_tons} Tonnellate CO2/anno`
                      : "—"}
                  </Badge>
                </td>

                <td className="px-5 py-5">
                  <Badge variant="custom" className="border-white/10 bg-white/[0.03] text-slate-200">
                    {row.plant_estimate || "STIMA: —"}
                  </Badge>
                </td>

                <td className="px-5 py-5">
                  <div className="text-xs text-muted-foreground">{row.address ?? ""}</div>
                </td>

                <td className="px-2 py-5">
                  <div className="flex items-center gap-2 justify-end">
                    {(() => {
                      const score = typeof row.solar_score === "number" ? row.solar_score : null;
                      const p = computePotentialFromName(row.business_name);
                      const blink = score !== null ? score > 90 : p.tier === "ECCELLENTE";

                      return (
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={!row.address && !row.business_name}
                          className={`actions-analyze-btn border-cyan-400/25 bg-cyan-400/10 text-cyan-100 hover:bg-cyan-400/15 hover:text-white ${
                            blink ? "animate-pulse shadow-[0_0_22px_rgba(34,211,238,0.22)]" : ""
                          }`}
                          asChild
                        >
                          <a
                            href={getSatelliteLink(row as any, city)}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <span className="mr-2">📡</span>
                            VEDI TETTO
                          </a>
                        </Button>
                      );
                    })()}
                    {row.lat !== null && row.lon !== null ? (
                      <button
                        onClick={() => onSolar(row)}
                        className="rounded-md border border-yellow-400/40 bg-yellow-500/15 px-3 py-1 text-[10px] font-semibold text-yellow-100 hover:bg-yellow-500/25"
                      >
                        ☀️ ANALISI TETTO
                      </button>
                    ) : null}
                  </div>
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
      <div className="px-5 pt-4 text-xs text-slate-500">
        Calcolo basato su analisi societaria, cubatura stimata e irraggiamento regionale.
      </div>
    </div>
  );
}

export function Dashboard() {
  const envDemoCity = (process.env.NEXT_PUBLIC_DEMO_CITY ?? "").trim();
  const envDemoCities = React.useMemo(() => {
    const raw = (process.env.NEXT_PUBLIC_DEMO_CITY ?? "").trim();
    if (!raw) return [] as string[];
    return raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }, []);
  const demoCategories = React.useMemo(() => {
    const raw = (process.env.NEXT_PUBLIC_DEMO_CATEGORIES ?? "").trim();
    if (!raw) return [] as string[];
    return raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }, []);

  const isDemoFromEnv = Boolean(envDemoCity) || demoCategories.length > 0;
  const isDemoFromUrl = React.useMemo(() => {
    if (typeof window === "undefined") return false;
    try {
      const u = new URL(window.location.href);
      return u.searchParams.get("demo") === "1";
    } catch {
      return false;
    }
  }, []);

  const isDemo = isDemoFromEnv || isDemoFromUrl;
  const demoCity = isDemo ? (envDemoCities[0] || envDemoCity || "Milano") : envDemoCity;

  const CUSTOM_CATEGORY_VALUE = "__custom__";

  const presets = React.useMemo(
    () => [
      "Fonderie",
      "Officine Meccaniche",
      "Stampaggio Plastica",
      "Industrie Tessili",
      "Cartiere",
      "Logistica e Magazzini",
      "Celle Frigorifere",
      "Supermercati",
      "Hotel",
      "Centri Sportivi",
      "Serre Agricole",
      "Aziende Ceramiche",
      "Vetrerie",
    ],
    []
  );

  const italyCityIndex = React.useMemo(
    () => [
      "Agrigento",
      "Alessandria",
      "Ancona",
      "Aosta",
      "Arezzo",
      "Ascoli Piceno",
      "Asti",
      "Avellino",
      "Bari",
      "Barletta",
      "Belluno",
      "Benevento",
      "Bergamo",
      "Biella",
      "Bologna",
      "Bolzano",
      "Brescia",
      "Brindisi",
      "Cagliari",
      "Caltanissetta",
      "Campobasso",
      "Caserta",
      "Catania",
      "Catanzaro",
      "Chieti",
      "Como",
      "Cosenza",
      "Cremona",
      "Crotone",
      "Cuneo",
      "Enna",
      "Fermo",
      "Ferrara",
      "Firenze",
      "Foggia",
      "Forlì",
      "Frosinone",
      "Genova",
      "Gorizia",
      "Grosseto",
      "Imperia",
      "Isernia",
      "La Spezia",
      "L'Aquila",
      "Latina",
      "Lecce",
      "Lecco",
      "Livorno",
      "Lodi",
      "Lucca",
      "Macerata",
      "Mantova",
      "Massa",
      "Matera",
      "Messina",
      "Milano",
      "Modena",
      "Monza",
      "Napoli",
      "Novara",
      "Nuoro",
      "Oristano",
      "Padova",
      "Palermo",
      "Parma",
      "Pavia",
      "Perugia",
      "Pesaro",
      "Pescara",
      "Piacenza",
      "Pisa",
      "Pistoia",
      "Pordenone",
      "Potenza",
      "Prato",
      "Ragusa",
      "Ravenna",
      "Reggio Calabria",
      "Reggio Emilia",
      "Rieti",
      "Rimini",
      "Roma",
      "Rovigo",
      "Salerno",
      "Sassari",
      "Savona",
      "Siena",
      "Siracusa",
      "Sondrio",
      "Taranto",
      "Teramo",
      "Terni",
      "Torino",
      "Trapani",
      "Trento",
      "Treviso",
      "Trieste",
      "Udine",
      "Varese",
      "Venezia",
      "Verbano-Cusio-Ossola",
      "Vercelli",
      "Verona",
      "Vibo Valentia",
      "Vicenza",
      "Viterbo",
    ],
    [],
  );

  const categoryPresets = React.useMemo(() => {
    if (!demoCategories.length) return presets;
    const allowed = new Set(demoCategories);
    const filtered = presets.filter((p) => allowed.has(p));
    const filteredSet = new Set(filtered);
    const missing = demoCategories.filter((c) => !filteredSet.has(c));
    return [...filtered, ...missing];
  }, [demoCategories, presets]);

  const [categoryMode, setCategoryMode] = React.useState<"preset" | "custom">(
    "preset",
  );
  const [categoryPreset, setCategoryPreset] = React.useState(
    demoCategories[0] ?? presets[0] ?? "Hotel",
  );
  const [categoryCustom, setCategoryCustom] = React.useState("");

  const category =
    categoryMode === "custom" ? categoryCustom : categoryPreset;

  const cityPresets = React.useMemo(
    () => [
      "Milano",
      "Roma",
      "Torino",
      "Napoli",
      "Bologna",
      "Firenze",
      "Venezia",
      "Palermo",
      "Genova",
      "Verona",
      "Custom…",
    ],
    []
  );

  const cityPresetOptions = React.useMemo(() => {
    if (!demoCity) return cityPresets;
    if (isDemo && envDemoCities.length) return envDemoCities;
    return [demoCity];
  }, [demoCity, cityPresets, envDemoCities, isDemo]);

  const [cityMode, setCityMode] = React.useState<"preset" | "custom">("preset");
  const [cityPreset, setCityPreset] = React.useState(demoCity || "Milano");
  const [cityCustom, setCityCustom] = React.useState("");

  const city = cityMode === "custom" ? cityCustom : cityPreset;
  const isCityInZoneDb = React.useMemo(() => {
    const c = city.trim();
    if (!c) return false;
    return Object.prototype.hasOwnProperty.call(zone_database, c);
  }, [city]);
  const zoneOptions = React.useMemo(() => {
    if (!isCityInZoneDb) return [] as string[];
    return zone_database[city.trim()] ?? [];
  }, [isCityInZoneDb, city]);

  const [zone, setZone] = React.useState("Tutta la città");

  React.useEffect(() => {
    const c = city.trim();
    if (!c) {
      setZone("Tutta la città");
      return;
    }
    if (!Object.prototype.hasOwnProperty.call(zone_database, c)) {
      setZone("Tutta la città");
      return;
    }
    const opts = zone_database[c] ?? [];
    if (!opts.length) {
      setZone("Tutta la città");
      return;
    }
    if (!zone || !opts.includes(zone)) {
      setZone(opts[0] ?? "Tutta la città");
    }
  }, [city]);

  const debouncedCityQuery = useDebouncedValue(demoCity ? "" : city.trim(), 250);
  const [citySuggestions, setCitySuggestions] = React.useState<string[]>([]);
  const [citySuggestOpen, setCitySuggestOpen] = React.useState(false);

  const cityStaticOptions = React.useMemo(() => {
    const merged = [
      ...italyCityIndex,
      ...cityPresets.filter((c) => c !== "Custom…"),
    ];
    return Array.from(new Set(merged.map((s) => String(s).trim()).filter(Boolean)));
  }, [italyCityIndex, cityPresets]);

  const cityDropdownOptions = React.useMemo(() => {
    const merged = [...cityStaticOptions, ...citySuggestions];
    return Array.from(new Set(merged.map((s) => String(s).trim()).filter(Boolean)));
  }, [cityStaticOptions, citySuggestions]);

  const cityFilteredOptions = React.useMemo(() => {
    if (isDemo && envDemoCities.length) return envDemoCities;
    const q = (demoCity ? "" : city.trim()).toLowerCase();
    const list = !q
      ? cityDropdownOptions
      : cityDropdownOptions.filter((s) => s.toLowerCase().includes(q));
    return list.slice(0, 30);
  }, [demoCity, city, cityDropdownOptions, envDemoCities, isDemo]);

  React.useEffect(() => {
    const q = debouncedCityQuery;
    if (!q || q.length < 2) {
      setCitySuggestions([]);
      return;
    }

    const ac = new AbortController();
    (async () => {
      try {
        const url =
          "https://nominatim.openstreetmap.org/search?format=jsonv2&countrycodes=it&addressdetails=1&limit=8&q=" +
          encodeURIComponent(q);
        const res = await fetch(url, {
          signal: ac.signal,
          headers: {
            "Accept": "application/json",
          },
        });
        if (!res.ok) {
          setCitySuggestions([]);
          return;
        }
        const data = (await res.json()) as Array<any>;
        const names = data
          .map((x) => {
            const a = x?.address;
            return (
              a?.city ||
              a?.town ||
              a?.village ||
              a?.hamlet ||
              a?.municipality ||
              x?.name ||
              ""
            );
          })
          .map((s) => String(s).trim())
          .filter(Boolean);
        const uniq = Array.from(new Set(names));
        setCitySuggestions(uniq);
      } catch (e) {
        if ((e as any)?.name === "AbortError") return;
        setCitySuggestions([]);
      }
    })();

    return () => ac.abort();
  }, [debouncedCityQuery]);

  React.useEffect(() => {
    if (!demoCategories.length) return;
    if (!demoCategories.includes(categoryPreset)) {
      setCategoryPreset(demoCategories[0]);
      setCategoryMode("preset");
      setCategoryCustom("");
    }
  }, [demoCategories, categoryPreset]);

  React.useEffect(() => {
    if (!demoCity) return;
    if (isDemo && envDemoCities.length) {
      if (!envDemoCities.includes(cityPreset)) {
        setCityPreset(envDemoCities[0] ?? demoCity);
        setCityMode("preset");
        setCityCustom("");
      }
      return;
    }
    if (cityPreset !== demoCity) {
      setCityPreset(demoCity);
      setCityMode("preset");
      setCityCustom("");
    }
  }, [demoCity, cityPreset, envDemoCities, isDemo]);

  const [job, setJob] = React.useState<JobStatus | null>(null);
  const [progress, setProgress] = React.useState(0);
  const [message, setMessage] = React.useState("—");
  const [state, setState] = React.useState<string | null>(null);
  const [rows, setRows] = React.useState<BusinessResult[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [sortDir, setSortDir] = React.useState<"desc" | "asc">("desc");
  const [showOnlyMobile, setShowOnlyMobile] = React.useState(false);

  const PAGE_SIZE = 25;
  const [page, setPage] = React.useState(0);

  const highPriorityTargets = React.useMemo(() => {
    return rows.filter((r) => {
      const speedCritical = (r.load_speed_s ?? 0) > 3;
      const noPixel = r.website_status === "HAS_WEBSITE" && !r.audit.has_facebook_pixel;
      const noSite = r.website_status === "MISSING_WEBSITE";
      const expSoon = isExpiringSoon(r.domain_expiration_date ?? null);
      return speedCritical || noPixel || noSite || expSoon;
    }).length;
  }, [rows]);

  const lastResultsCountRef = React.useRef(0);
  const resultsFetchInFlightRef = React.useRef(false);


  const filteredRows = React.useMemo(() => {
    if (!showOnlyMobile) return rows;
    return rows.filter((r) => isMobilePhone(r.phone ?? null));
  }, [rows, showOnlyMobile]);

  const sortedRows = React.useMemo(() => {
    const base = [...filteredRows];
    const score = (r: BusinessResult) => {
      if (r.website_status === "MISSING_WEBSITE") return 2000;
      if (r.website_status === "HAS_WEBSITE" && !r.audit.has_facebook_pixel) return 1500;
      let s = 0;
      if (!r.audit.has_facebook_pixel) s += 200;
      if (!r.audit.has_gtm) s += 60;
      if (!r.audit.has_ssl) s += 30;
      if (!r.audit.is_mobile_responsive) s += 20;
      return s;
    };

    const dir = sortDir === "desc" ? -1 : 1;
    return base.sort((a, b) => (score(a) - score(b)) * dir);
  }, [filteredRows, sortDir]);

  React.useEffect(() => {
    setPage(0);
  }, [sortDir, rows.length, showOnlyMobile]);
  const totalPages = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE));
  const pageSafe = Math.min(Math.max(0, page), totalPages - 1);
  const pagedRows = React.useMemo(() => {
    const start = pageSafe * PAGE_SIZE;
    return sortedRows.slice(start, start + PAGE_SIZE);
  }, [sortedRows, pageSafe]);

  async function onStart() {
    setLoading(true);
    setRows([]);
    setProgress(0);
    setMessage("Starting...");
    lastResultsCountRef.current = 0;

    try {
      const zoneValue = String(zone || "").trim();
      const selectedCategory = String(
        categoryMode === "custom" ? categoryCustom : categoryPreset,
      ).trim();
      const selectedCity = String(city).trim();
      const j = await startJob(selectedCategory, selectedCity, zoneValue);
      setJob(j);
      setState(j.state);

      let pollingTimer: number | null = null;
      const stopPolling = () => {
        if (pollingTimer) {
          window.clearInterval(pollingTimer);
          pollingTimer = null;
        }
      };

      const startPolling = () => {
        if (pollingTimer) return;
        pollingTimer = window.setInterval(async () => {
          try {
            const s = await fetchJob(j.id);
            setProgress(s.progress ?? 0);
            setMessage(s.message ?? "");
            setState(s.state ?? null);

            const nextCount = Math.max(0, Number(s.results_count ?? 0) || 0);
            if (
              nextCount > lastResultsCountRef.current &&
              !resultsFetchInFlightRef.current &&
              s.state !== "done"
            ) {
              resultsFetchInFlightRef.current = true;
              lastResultsCountRef.current = nextCount;
              try {
                const data = await fetchResults(j.id);
                setRows(data);
              } finally {
                resultsFetchInFlightRef.current = false;
              }
            }

            if (s.state === "done") {
              stopPolling();
              const data = await fetchResults(j.id);
              setRows(data);
              setLoading(false);
            }

            if (s.state === "error") {
              stopPolling();
              setLoading(false);
              setRows([]);
              setMessage(s.error ? `Errore: ${s.error}` : "Errore durante l'audit");
            }
          } catch {
            // keep trying
          }
        }, 1000);
      };

      const ev = new EventSource(`${BACKEND_URL}/jobs/${j.id}/events`);
      ev.onmessage = async (e) => {
        let parsed: any = null;
        try {
          parsed = JSON.parse(String(e.data || "{}"));
        } catch {
          parsed = null;
        }

        if (!parsed) return;

        if (parsed.progress !== undefined && parsed.progress !== null) {
          setProgress(parsed.progress ?? 0);
        }
        if (parsed.message !== undefined && parsed.message !== null) {
          setMessage(parsed.message ?? "");
        }
        if (parsed.state !== undefined && parsed.state !== null) {
          setState(parsed.state ?? null);
        }

        const nextCount = Math.max(0, Number(parsed.results_count ?? 0) || 0);
        if (
          nextCount > lastResultsCountRef.current &&
          !resultsFetchInFlightRef.current &&
          parsed.state !== "done"
        ) {
          resultsFetchInFlightRef.current = true;
          lastResultsCountRef.current = nextCount;
          try {
            const data = await fetchResults(j.id);
            setRows(data);
          } catch {
            // ignore
          } finally {
            resultsFetchInFlightRef.current = false;
          }
        }

        if (parsed.state === "done") {
          ev.close();
          stopPolling();
          const data = await fetchResults(j.id);
          setRows(data);
          setLoading(false);
        }

        if (parsed.state === "error") {
          ev.close();
          stopPolling();
          setRows([]);
          setLoading(false);
          setMessage(parsed.error ? `Errore: ${parsed.error}` : "Errore durante l'audit");
        }
      };

      ev.onerror = async () => {
        ev.close();
        // SSE can be flaky on some setups; fall back to polling.
        setMessage("SSE connection dropped. Switching to polling...");
        startPolling();
      };
    } catch (e) {
      console.log("startJob failed", e);
      setMessage("Failed to start job. Ensure backend is running.");
      setLoading(false);
    }
  }

  function exportCsv() {
    if (!job) return;
    window.open(`${BACKEND_URL}/jobs/${job.id}/export.csv`, "_blank");
  }

  const [techOpen, setTechOpen] = React.useState(false);
  const [techRow, setTechRow] = React.useState<BusinessResult | null>(null);
  const [techLoading, setTechLoading] = React.useState(false);
  const [techResult, setTechResult] = React.useState<TechnicalAuditResult | null>(null);
  const [techError, setTechError] = React.useState<string | null>(null);

  const [solarOpen, setSolarOpen] = React.useState(false);
  const [solarRow, setSolarRow] = React.useState<BusinessResult | null>(null);
  const [solarLoading, setSolarLoading] = React.useState(false);
  const [solarResult, setSolarResult] = React.useState<any>(null);
  const [solarError, setSolarError] = React.useState<string | null>(null);

  async function openTechnicalAudit(row: BusinessResult) {
    if (!job) return;
    setTechRow(row);
    setTechOpen(true);
    setTechLoading(true);
    setTechResult(null);
    setTechError(null);
    try {
      const r = await fetchTechnicalAudit(job.id, row.result_index);
      setTechResult(r);
    } catch (e) {
      setTechError(e instanceof Error ? e.message : "Errore durante l'analisi tecnica");
    } finally {
      setTechLoading(false);
    }
  }

  async function openSolarAnalysis(row: BusinessResult) {
    if (!job) return;
    setSolarRow(row);
    setSolarOpen(true);
    setSolarLoading(true);
    setSolarResult(null);
    setSolarError(null);
    try {
      const res = await fetch(
        `${BACKEND_URL}/jobs/${job.id}/results/${row.result_index}/solar-analysis`
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Errore" }));
        throw new Error(err.detail || "Errore analisi solare");
      }
      setSolarResult(await res.json());
    } catch (e) {
      setSolarError(e instanceof Error ? e.message : "Errore");
    } finally {
      setSolarLoading(false);
    }
  }

  return (
    <div className="mx-auto px-6 py-20 md:px-10">
      <div className="mx-auto w-[95vw] max-w-[1800px]">
        <div className="text-center">
          <div className="text-xs font-medium tracking-widest text-slate-400">
            SOLAR SNIPER
          </div>
          <h1 className="mt-6 text-[3.75rem] font-extrabold leading-[1.02] tracking-tight text-primary">
            SOLAR SNIPER
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-sm text-slate-400">
            Inserisci categoria e città. Aspetta ~2 minuti. Solar Sniper genera una scheda completa con stima
            consumi/potenziale FV, link satellitare e contatti utili (telefono/email).
          </p>

          <div className="mt-12">
            <div className="glass-panel px-10 py-8">
              <div className="text-xs font-medium tracking-widest text-slate-400">
                TARGET PRIORITARI
              </div>
              <div className="mt-3 flex items-end justify-center gap-3">
                <div className="text-5xl font-semibold tracking-tight text-slate-100">
                  {highPriorityTargets}
                </div>
                <div className="pb-1 text-sm font-medium text-slate-400">attività</div>
              </div>
              <div className="mt-3 text-sm text-slate-400">
                Selezionati automaticamente per potenziale FV e completezza delle informazioni.
              </div>
              <div className="mt-5 flex justify-center">
                <Button
                  variant="secondary"
                  onClick={exportCsv}
                  disabled={!job || rows.length === 0}
                >
                  <FileDown className="mr-2 h-4 w-4" />
                  Export to CSV
                </Button>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-16">
          <div className="glass-capsule relative z-50 flex flex-col gap-5 p-5 md:flex-row md:items-center">
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">Categoria Target</div>
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <select
                  value={categoryMode === "custom" ? CUSTOM_CATEGORY_VALUE : categoryPreset}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (v === CUSTOM_CATEGORY_VALUE) {
                      if (isDemo) return;
                      setCategoryMode("custom");
                      setCategoryCustom((prev) => {
                        const p = String(prev || "").trim();
                        if (p.length > 0) return prev;
                        return String(categoryPreset || "");
                      });
                      return;
                    }
                    setCategoryMode("preset");
                    setCategoryPreset(v);
                  }}
                  className="h-[60px] w-full rounded-xl border border-white/[0.08] bg-transparent px-5 text-base text-slate-100 shadow-sm outline-none transition-colors focus-visible:border-emerald-400/40 focus-visible:ring-0 focus-visible:shadow-[0_0_20px_rgba(0,230,118,0.22)]"
                >
                  {categoryPresets.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                  {isDemo ? null : (
                    <option value={CUSTOM_CATEGORY_VALUE}>Custom...</option>
                  )}
                </select>

                <Input
                  value={categoryCustom}
                  onChange={(e) => {
                    if (isDemo) return;
                    setCategoryMode("custom");
                    setCategoryCustom(e.target.value);
                  }}
                  placeholder="Custom category..."
                  disabled={isDemo}
                />
              </div>
            </div>
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground">City</div>
              <div className="space-y-3">
                <div>
                  {isDemo && envDemoCities.length > 1 ? (
                    <select
                      className="h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm"
                      value={cityPreset}
                      onChange={(e) => {
                        setCityMode("preset");
                        setCityPreset(e.target.value);
                        setCityCustom("");
                      }}
                    >
                      {envDemoCities.map((s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <>
                      <Input
                        list="city-options"
                        placeholder="Scrivi città/paese…"
                        value={demoCity ? demoCity : city}
                        disabled={Boolean(demoCity)}
                        onChange={(e) => {
                          const v = e.target.value;
                          setCityMode("custom");
                          setCityCustom(v);
                        }}
                      />
                      <datalist id="city-options">
                        {cityFilteredOptions.map((s) => (
                          <option key={s} value={s} />
                        ))}
                      </datalist>
                    </>
                  )}
                </div>

                <div>
                  <div className="mb-2 text-xs text-muted-foreground">Zona</div>
                  <Input
                    list={isCityInZoneDb ? "zone-options" : undefined}
                    placeholder={
                      isCityInZoneDb
                        ? "Seleziona o scrivi zona…"
                        : "Scrivi zona (opzionale)…"
                    }
                    value={zone}
                    onChange={(e) => setZone(e.target.value)}
                  />
                  {isCityInZoneDb ? (
                    <datalist id="zone-options">
                      {zoneOptions.map((z) => (
                        <option key={z} value={z} />
                      ))}
                    </datalist>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="flex items-end justify-center md:justify-end">
              <Button
                className="btn-glow neon-glow h-[60px] w-full px-8 text-white hover:opacity-95 md:w-auto"
                onClick={onStart}
                disabled={loading || category.trim().length < 2 || city.trim().length < 2}
              >
                <Rocket className="mr-2 h-4 w-4" />
                Avvia Solar Sniper
              </Button>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center justify-center gap-3">
            <Button
              type="button"
              onClick={() => {
                if (isDemo) return;
                setCategoryMode("custom");
                setCategoryCustom("Fabbrica, Produzione");
                setCityMode("custom");
                setCityCustom(city);
              }}
            >
              🏭 FABBRICHE
            </Button>
            <Button
              type="button"
              onClick={() => {
                if (isDemo) return;
                setCategoryMode("custom");
                setCategoryCustom("Hotel, Albergo");
              }}
            >
              🏨 HOTEL
            </Button>
            <Button
              type="button"
              onClick={() => {
                if (isDemo) return;
                setCategoryMode("custom");
                setCategoryCustom("Ristorante");
              }}
            >
              🍽️ RISTORANTI
            </Button>
          </div>

          <div className="mt-4">
            <Progress value={progress} />
            <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
              <span>{message || "—"}</span>
              <span>{progress}%</span>
            </div>
          </div>

          <AnimatePresence>

          {!loading && rows.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="glass-panel p-8"
            >
              <div className="text-sm font-medium">No results yet</div>
              <div className="mt-2 text-sm text-muted-foreground">
                Inserisci categoria e città e premi <span className="text-foreground">Avvia Solar Sniper</span>.
              </div>
            </motion.div>
          ) : null}

          {rows.length > 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              className="space-y-3"
            >
              {sortedRows.length > PAGE_SIZE ? (
                <div className="flex items-center justify-center gap-3 text-xs text-slate-400">
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={pageSafe === 0}
                  >
                    Prev
                  </Button>
                  <span>
                    Page {pageSafe + 1} / {totalPages}
                  </span>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={pageSafe >= totalPages - 1}
                  >
                    Next
                  </Button>
                </div>
              ) : null}

              <div className="flex items-center justify-center">
                <Button
                  variant="secondary"
                  onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
                >
                  {sortDir === "desc" ? (
                    <ArrowDown className="mr-2 h-4 w-4" />
                  ) : (
                    <ArrowUp className="mr-2 h-4 w-4" />
                  )}
                  Sort by priority
                </Button>

                <Button
                  variant={showOnlyMobile ? "default" : "secondary"}
                  className="ml-3"
                  onClick={() => setShowOnlyMobile((v) => !v)}
                  disabled={rows.length === 0}
                >
                  📱 MOSTRA SOLO CELLULARI
                </Button>
              </div>

              <ResultsTable
                rows={pagedRows}
                city={city}
                onTechnical={openTechnicalAudit}
                onSolar={openSolarAnalysis}
              />
            </motion.div>
          ) : null}

        </AnimatePresence>
      </div>

      <Dialog
        open={techOpen}
        onOpenChange={(v) => {
          setTechOpen(v);
          if (!v) {
            setTechRow(null);
            setTechResult(null);
            setTechError(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>🔍 ANALISI TECNICA</DialogTitle>
            <DialogDescription>
              {techRow?.business_name ?? ""}
            </DialogDescription>
          </DialogHeader>

          {techRow ? (
            <div className="flex flex-wrap items-center gap-2">
              {isExpiringSoon(techRow.domain_expiration_date ?? null) ? (
                <Badge variant="expiring_soon">EXPIRING SOON</Badge>
              ) : null}
              {isLegacyBrand(techRow.domain_creation_date ?? null) ? (
                <Badge variant="legacy_brand">LEGACY BRAND</Badge>
              ) : null}
              {techRow.domain_creation_date ? (
                <span className="text-xs text-slate-400">
                  Created: {techRow.domain_creation_date}
                </span>
              ) : null}
              {techRow.domain_expiration_date ? (
                <span className="text-xs text-slate-400">
                  Expires: {techRow.domain_expiration_date}
                </span>
              ) : null}
              {techRow.load_speed_s !== null && techRow.load_speed_s !== undefined ? (
                <span className="text-xs text-slate-400">
                  Load: {techRow.load_speed_s.toFixed(2)}s
                </span>
              ) : null}
            </div>
          ) : null}

          <div className="rounded-md border border-border bg-[#0b0b0c] p-4 font-mono text-[12px] leading-relaxed text-[#eaeaea]">
            {techLoading ? (
              <div>Analisi in corso...</div>
            ) : techError ? (
              <div className="text-red-300">{techError}</div>
            ) : techResult ? (
              <div className="space-y-3">
                {techResult.issues.length === 0 ? (
                  <div>Nessun errore critico rilevato.</div>
                ) : (
                  techResult.issues.map((it, i) => (
                    <div key={`${it.code}-${i}`} className="rounded border border-red-500/30 bg-red-500/10 p-3">
                      <div className="text-red-200 font-semibold">
                        {it.severity.toUpperCase()}: {it.message}
                      </div>
                      {it.line ? (
                        <div className="mt-1 text-red-100/80">Linea: {it.line}</div>
                      ) : null}
                      {it.context ? (
                        <pre className="mt-2 whitespace-pre-wrap text-[#cbd5e1]">{it.context}</pre>
                      ) : null}
                    </div>
                  ))
                )}
              </div>
            ) : (
              <div>—</div>
            )}
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setTechOpen(false)}>
              Chiudi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={solarOpen}
        onOpenChange={(v) => {
          setSolarOpen(v);
          if (!v) {
            setSolarRow(null);
            setSolarResult(null);
            setSolarError(null);
          }
        }}
      >
        <DialogContent className="sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>☀️ ANALISI TETTO</DialogTitle>
            <DialogDescription>
              {solarRow?.business_name ?? ""}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {solarLoading ? (
              <div className="text-center py-8">Analisi solare in corso...</div>
            ) : solarError ? (
              <div className="text-red-300 text-center py-8">{solarError}</div>
            ) : solarResult ? (
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4">
                    <div className="text-sm text-green-200 font-semibold">Max Pannelli Installabili</div>
                    <div className="text-2xl font-bold text-green-100">{solarResult.max_panels ?? "—"}</div>
                  </div>
                  <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-4">
                    <div className="text-sm text-blue-200 font-semibold">Area Tetto Utilizzabile</div>
                    <div className="text-2xl font-bold text-blue-100">{solarResult.max_area_m2 ?? "—"} m²</div>
                  </div>
                  <div className="rounded-lg border border-yellow-500/30 bg-yellow-500/10 p-4">
                    <div className="text-sm text-yellow-200 font-semibold">Ore di Sole / Anno</div>
                    <div className="text-2xl font-bold text-yellow-100">{solarResult.sunshine_hours_year ?? "—"}</div>
                  </div>
                  <div className="rounded-lg border border-purple-500/30 bg-purple-500/10 p-4">
                    <div className="text-sm text-purple-200 font-semibold">Area Tetto Totale</div>
                    <div className="text-2xl font-bold text-purple-100">{solarResult.roof_area_m2 ?? "—"} m²</div>
                  </div>
                </div>

                <div>
                  <h3 className="text-lg font-semibold mb-3">Configurazioni Impianto</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full border-collapse border border-slate-600">
                      <thead>
                        <tr className="bg-slate-700">
                          <th className="border border-slate-600 px-4 py-2 text-left">Pannelli</th>
                          <th className="border border-slate-600 px-4 py-2 text-left">kWp</th>
                          <th className="border border-slate-600 px-4 py-2 text-left">kWh Annui</th>
                        </tr>
                      </thead>
                      <tbody>
                        {solarResult.panel_configs?.map(
                          (
                            config: { panels?: number; kwp?: number; yearly_kwh?: number },
                            i: number,
                          ) => (
                          <tr key={i} className="bg-slate-800">
                            <td className="border border-slate-600 px-4 py-2">{config.panels ?? "—"}</td>
                            <td className="border border-slate-600 px-4 py-2">{config.kwp ?? "—"}</td>
                            <td className="border border-slate-600 px-4 py-2">{config.yearly_kwh ?? "—"}</td>
                          </tr>
                          ),
                        )}
                        {(!solarResult.panel_configs || solarResult.panel_configs.length === 0) && (
                          <tr>
                            <td colSpan={3} className="text-center py-4">Nessuna configurazione</td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="flex flex-wrap gap-4 text-sm">
                  {solarResult.imagery_date && (
                    <div>
                      <span className="font-semibold">Data Immagine:</span> {solarResult.imagery_date}
                    </div>
                  )}
                  {solarResult.imagery_quality && (
                    <div>
                      <span className="font-semibold">Qualità Immagine:</span> {solarResult.imagery_quality}
                    </div>
                  )}
                  {solarResult.center && (
                    <a
                      href={`https://earth.google.com/web/search/${solarResult.center.longitude},${solarResult.center.latitude}/@${solarResult.center.longitude},${solarResult.center.latitude},100a,35y,0h,0t,0r`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 underline"
                    >
                      Apri in Google Earth
                    </a>
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <DialogFooter>
            <Button variant="secondary" onClick={() => setSolarOpen(false)}>
              Chiudi
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      </div>
    </div>
  );
}
