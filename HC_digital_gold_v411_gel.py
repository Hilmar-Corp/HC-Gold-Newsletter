#!/usr/bin/env python3
"""
HilmarCorp Research — V4.1 GEL
======================================

L'or numérique est-il une bonne comparaison ?
Bitcoin et l'or répondent-ils réellement aux mêmes risques ?

Objet
-----
Tester si Bitcoin et l'or présentent des sensibilités suffisamment proches aux
principaux facteurs macrofinanciers pour que l'analogie « or numérique » ait un
sens du point de vue de l'allocation.

Architecture V4.1
---------------
1. Cœur factoriel 2017–2026 :
   - actions américaines ;
   - dollar large ;
   - taux réel US 10 ans.
   Le crédit et le VIX n'entrent PAS dans la spécification primaire.

2. Aversion au risque :
   - analyses conditionnelles et de queues via le VIX ;
   - extension factorielle avec variation du VIX orthogonalisée au rendement actions.

3. Crédit :
   - BAA10Y comme proxy de spread de crédit quotidien couvrant l'échantillon complet ;
   - ICE BofA HY OAS traité séparément comme test récent, jamais comme facteur primaire.

4. Inflation :
   - CPI-U non désaisonnalisé (CPIAUCNS) ;
   - dates effectives de publication récupérées dans les calendriers BLS ;
   - état d'inflation connu au marché construit à partir de la dernière publication ;
   - étude événementielle au niveau des publications ;
   - aucune « surprise d'inflation » n'est inventée sans données de consensus.

5. Certification :
   - manifeste de couverture ;
   - fail automatique si le cœur factoriel perd une part substantielle de l'échantillon ;
   - fail si une variable récente contamine la régression primaire ;
   - fail si le calendrier CPI est incomplet, incohérent ou non causal ;
   - fail si les tests leave-one-year-out ne retirent pas réellement l'année concernée.

Ce script est un protocole de recherche descriptif. Il ne constitue ni une stratégie
d'investissement, ni un moteur de décision, ni une recommandation.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import statsmodels.api as sm
import exchange_calendars as xcals
from bs4 import BeautifulSoup
from scipy.stats import chi2


# ===========================================================================
# CONFIGURATION
# ===========================================================================

DEFAULT_START = "2017-08-17"

YAHOO_CHART_ENDPOINTS = (
    "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
    "https://query2.finance.yahoo.com/v8/finance/chart/{symbol}",
)

BINANCE_KLINES = "https://api.binance.com/api/v3/klines"
FRED_ENDPOINT = "https://fred.stlouisfed.org/graph/fredgraph.csv"
BLS_YEAR_SCHEDULE_CANDIDATES = (
    "https://www.bls.gov/schedule/{year}/",
    "https://www.bls.gov/schedule/{year}/home.htm",
)

FRED_SERIES = {
    "sp500": "SP500",
    "real10y": "DFII10",
    "usd_broad": "DTWEXBGS",
    "vix": "VIXCLS",
    "nfci": "NFCI",
    "baa10y": "BAA10Y",
    "hy_oas_recent": "BAMLH0A0HYM2",
    "cpi_nsa": "CPIAUCNS",
}

CORE_FACTORS = ("equity", "usd", "real_rate")
FORBIDDEN_CORE_FACTORS = ("hy_oas_recent", "hy_oas_recent_change", "credit_baa", "risk_aversion")
CORE_MIN_COVERAGE = 0.97
CORE_END_MAX_LAG_BDAYS = 7
CORE_START_MAX_LAG_BDAYS = 10
BTC_MISSING_SESSION_MAX = 2
BTC_MISSING_SHARE_MAX = 0.0015
ARCX_CALENDAR = "ARCX"

FACTOR_LABELS = {
    "equity": "Actions américaines",
    "usd": "Dollar large",
    "real_rate": "Taux réel US 10 ans",
    "risk_aversion": "Aversion au risque",
    "risk_aversion_orth": "Aversion au risque orthogonalisée",
    "credit_baa": "Spread de crédit Baa",
    "hy_oas_recent_change": "HY OAS — fenêtre récente",
    "liquidity_stress_ex_post": "Tensions financières ex post (NFCI révisé)",
    "inflation_yoy_available": "Inflation publiée disponible",
}

ECONOMIC_SHOCKS = {
    "equity": -0.05,      # -5 % actions
    "usd": -0.02,         # -2 % dollar large
    "real_rate": 0.50,    # +50 pb, DFII10 étant en points de pourcentage
}

ECONOMIC_SHOCK_LABELS = {
    "equity": "Actions -5 %",
    "usd": "Dollar -2 %",
    "real_rate": "Taux réel +50 pb",
}


@dataclass(frozen=True)
class Config:
    start: str = DEFAULT_START
    end: str = ""
    horizons: tuple[int, ...] = (1, 5, 20)
    rolling_window: int = 252
    rolling_min_obs: int = 180
    quantiles: int = 5
    bootstrap_reps: int = 2000
    bootstrap_block: int = 20
    random_seed: int = 42
    winsor_limits: tuple[float, float] = (0.01, 0.99)
    min_regression_obs: int = 250
    etf_break: str = "2024-01-11"
    covid_break: str = "2020-03-01"


# ===========================================================================
# HTTP / CACHE
# ===========================================================================

def http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/151.0 Safari/537.36 HilmarCorp-Research/4.1"
        ),
        "Accept": "text/html,text/csv,application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    })
    return s


def request_with_retry(
    session: requests.Session,
    url: str,
    *,
    params: dict | None = None,
    attempts: int = 4,
    label: str = "HTTP",
) -> requests.Response:
    timeouts = [(10, 45), (10, 90), (15, 180), (20, 240)]
    last_error: Exception | None = None

    for i in range(attempts):
        try:
            print(f"      {label} — tentative {i+1}/{attempts}...")
            r = session.get(url, params=params, timeout=timeouts[min(i, len(timeouts)-1)])
            r.raise_for_status()
            return r
        except Exception as exc:
            last_error = exc
            if i + 1 < attempts:
                wait = 2 ** i
                print(f"      {label} indisponible: {exc}. Nouvelle tentative dans {wait}s.")
                time.sleep(wait)

    raise RuntimeError(f"{label}: échec après {attempts} tentatives: {last_error}") from last_error


def fetch_fred(
    series_id: str,
    session: requests.Session,
    start: str,
    end: str,
    cache_dir: Path,
) -> pd.Series:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{series_id}.csv"

    params = {"id": series_id, "cosd": start, "coed": end}

    try:
        r = request_with_retry(
            session,
            FRED_ENDPOINT,
            params=params,
            label=f"FRED {series_id}",
        )
        head = r.text[:200].lower()
        if "<html" in head or "<!doctype" in head:
            raise RuntimeError(f"FRED {series_id}: réponse HTML inattendue")

        df = pd.read_csv(io.StringIO(r.text))
        if df.shape[1] != 2:
            raise RuntimeError(f"FRED {series_id}: colonnes inattendues {df.columns.tolist()}")

        date_col, value_col = df.columns
        out = pd.DataFrame({
            "date": pd.to_datetime(df[date_col], errors="coerce"),
            "value": pd.to_numeric(df[value_col], errors="coerce"),
        }).dropna(subset=["date"])

        out = out.drop_duplicates("date", keep="last").sort_values("date")
        out.to_csv(cache_path, index=False)

    except Exception as exc:
        if not cache_path.exists():
            raise
        print(f"      ATTENTION — {series_id}: reprise sur cache local ({exc})")
        out = pd.read_csv(cache_path)
        out["date"] = pd.to_datetime(out["date"], errors="coerce")
        out["value"] = pd.to_numeric(out["value"], errors="coerce")
        out = out.dropna(subset=["date"]).sort_values("date")

    return pd.Series(out["value"].to_numpy(), index=out["date"], name=series_id)


def fetch_yahoo_daily(
    symbol: str,
    start: str,
    end: str,
    session: requests.Session,
) -> pd.DataFrame:
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())

    params = {
        "period1": start_ts,
        "period2": end_ts,
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }

    last_error: Exception | None = None

    for endpoint in YAHOO_CHART_ENDPOINTS:
        try:
            r = request_with_retry(
                session,
                endpoint.format(symbol=symbol),
                params=params,
                attempts=2,
                label=f"Yahoo {symbol}",
            )
            payload = r.json()
            chart = payload.get("chart", {})
            if chart.get("error"):
                raise RuntimeError(chart["error"])

            results = chart.get("result")
            if not results:
                raise RuntimeError("résultat vide")

            result = results[0]
            timestamps = result.get("timestamp") or []
            quote = (result.get("indicators", {}).get("quote") or [{}])[0]
            adj_list = result.get("indicators", {}).get("adjclose") or [{}]
            adj = adj_list[0].get("adjclose") if adj_list else None

            idx = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize()
            df = pd.DataFrame(index=idx)
            df.index.name = "Date"

            for src, dst in [
                ("open", "Open"), ("high", "High"), ("low", "Low"),
                ("close", "Close"), ("volume", "Volume"),
            ]:
                vals = quote.get(src)
                if vals is not None:
                    df[dst] = pd.to_numeric(vals, errors="coerce")

            df["Adj Close"] = (
                pd.to_numeric(adj, errors="coerce")
                if adj is not None
                else df["Close"]
            )

            df = (
                df[~df.index.duplicated(keep="last")]
                .sort_index()
                .loc[pd.Timestamp(start):pd.Timestamp(end)]
            )

            if df.empty:
                raise RuntimeError("données vides")
            return df

        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Yahoo {symbol}: échec: {last_error}") from last_error


def fetch_binance_hourly(
    start: str,
    end: str,
    session: requests.Session,
    symbol: str = "BTCUSDT",
) -> pd.DataFrame:
    start_ms = int(pd.Timestamp(start, tz="UTC").timestamp() * 1000)
    end_ms = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp() * 1000) - 1

    rows: list[list] = []
    cursor = start_ms

    while cursor <= end_ms:
        params = {
            "symbol": symbol,
            "interval": "1h",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": 1000,
        }
        r = request_with_retry(
            session,
            BINANCE_KLINES,
            params=params,
            attempts=3,
            label="Binance BTCUSDT 1h",
        )
        batch = r.json()
        if not batch:
            break

        rows.extend(batch)
        last_open = int(batch[-1][0])
        nxt = last_open + 3_600_000
        if nxt <= cursor:
            raise RuntimeError("Pagination Binance bloquée")
        cursor = nxt
        time.sleep(0.04)

    if not rows:
        raise RuntimeError("Aucune donnée Binance")

    cols = [
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_base", "taker_quote", "ignore",
    ]
    df = pd.DataFrame(rows, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    return (
        df.drop_duplicates("open_time", keep="last")
        .sort_values("open_time")
        .set_index("open_time")
    )


# ===========================================================================
# BLS CPI — DATES DE PUBLICATION EFFECTIVES
# ===========================================================================

MONTH_MAP = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}


def parse_bls_schedule_html(html: str, schedule_year: int) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    rows = []

    for tr in soup.find_all("tr"):
        cells = [" ".join(td.get_text(" ", strip=True).split()) for td in tr.find_all(["td", "th"])]
        if len(cells) < 3:
            continue

        date_text, time_text, release_text = cells[0], cells[1], cells[2]
        if "Consumer Price Index for " not in release_text:
            continue

        # Ex.: "Consumer Price Index for December 2024"
        m = re.search(
            r"Consumer Price Index for "
            r"(January|February|March|April|May|June|July|August|September|October|November|December) "
            r"(\d{4})",
            release_text,
        )
        if not m:
            continue

        ref_month_name, ref_year_s = m.groups()
        ref_year = int(ref_year_s)
        ref_month = MONTH_MAP[ref_month_name]

        release_date = pd.to_datetime(date_text, errors="coerce")
        if pd.isna(release_date):
            continue

        rows.append({
            "schedule_year": schedule_year,
            "reference_month": pd.Timestamp(ref_year, ref_month, 1),
            "release_date": release_date.normalize(),
            "release_time_text": time_text,
            "release_text": release_text,
        })

    if not rows:
        return pd.DataFrame(
            columns=[
                "schedule_year", "reference_month", "release_date",
                "release_time_text", "release_text",
            ]
        )

    out = pd.DataFrame(rows)
    out = (
        out.sort_values(["reference_month", "release_date"])
        .drop_duplicates("reference_month", keep="last")
        .reset_index(drop=True)
    )
    return out


def fetch_bls_cpi_calendar(
    start_year: int,
    end_year: int,
    session: requests.Session,
    cache_dir: Path,
) -> pd.DataFrame:
    """
    Télécharge les calendriers BLS annuels avec validation sémantique.

    Le BLS n'utilise pas une structure d'URL parfaitement stable d'une année
    à l'autre. On essaie donc /schedule/YYYY/ puis /schedule/YYYY/home.htm.
    Un cache n'est écrit qu'après validation qu'une page contient et parse
    effectivement des entrées CPI.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    frames = []

    for year in range(start_year, end_year + 1):
        cache_path = cache_dir / f"bls_schedule_{year}.html"
        parsed = pd.DataFrame()
        errors = []

        for template in BLS_YEAR_SCHEDULE_CANDIDATES:
            url = template.format(year=year)
            try:
                r = request_with_retry(
                    session,
                    url,
                    attempts=3,
                    label=f"BLS calendrier {year}",
                )
                html = r.text

                if "Consumer Price Index" not in html:
                    raise RuntimeError(f"page reçue sans entrées CPI: {url}")

                candidate = parse_bls_schedule_html(html, year)
                if candidate.empty:
                    raise RuntimeError(f"page CPI non parsable: {url}")

                cache_path.write_text(html, encoding="utf-8")
                parsed = candidate
                print(
                    f"      BLS {year} — OK via {url} "
                    f"({len(parsed)} publication(s) CPI)"
                )
                break

            except Exception as exc:
                errors.append(f"{url}: {exc}")

        if parsed.empty and cache_path.exists():
            try:
                html = cache_path.read_text(encoding="utf-8")
                if "Consumer Price Index" not in html:
                    raise RuntimeError("cache sans entrées CPI")

                parsed = parse_bls_schedule_html(html, year)
                if parsed.empty:
                    raise RuntimeError("cache CPI non parsable")

                print(
                    f"      ATTENTION — BLS {year}: reprise sur cache validé "
                    f"({len(parsed)} publication(s) CPI)"
                )
            except Exception as exc:
                errors.append(f"cache {cache_path}: {exc}")
                parsed = pd.DataFrame()

        if parsed.empty:
            raise RuntimeError(
                f"BLS {year}: impossible d'obtenir un calendrier CPI valide. "
                f"Détails: {' | '.join(errors)}"
            )

        frames.append(parsed)

    out = pd.concat(frames, ignore_index=True)
    out = (
        out.sort_values(["reference_month", "release_date"])
        .drop_duplicates("reference_month", keep="last")
        .reset_index(drop=True)
    )
    return out


def build_cpi_release_table(
    cpi_nsa: pd.Series,
    calendar: pd.DataFrame,
    start: str,
    end: str,
) -> pd.DataFrame:
    cpi = cpi_nsa.copy()
    cpi.index = pd.to_datetime(cpi.index).to_period("M").to_timestamp()
    cpi = cpi[~cpi.index.duplicated(keep="last")].sort_index()

    yoy = cpi.pct_change(12)
    yoy.name = "cpi_yoy"

    cal = calendar.copy()
    cal["reference_month"] = pd.to_datetime(cal["reference_month"]).dt.to_period("M").dt.to_timestamp()
    cal["cpi_yoy"] = cal["reference_month"].map(yoy)

    cal = cal.dropna(subset=["cpi_yoy"]).copy()
    cal["inflation_acceleration"] = cal["cpi_yoy"].diff()

    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    # Conserver une publication antérieure pour initialiser l'état disponible.
    cal = cal[
        (cal["release_date"] <= end_ts) &
        (cal["reference_month"] >= start_ts - pd.DateOffset(months=18))
    ].copy()

    cal["reference_month_end"] = cal["reference_month"] + pd.offsets.MonthEnd(0)
    cal["causal_release"] = cal["release_date"] > cal["reference_month_end"]

    return cal.reset_index(drop=True)


# ===========================================================================
# ALIGNEMENT TEMPOREL ET PANEL
# ===========================================================================

def build_arcx_close_schedule(
    trading_dates: Iterable[pd.Timestamp],
) -> pd.DataFrame:
    """
    Construit les heures de clôture effectives de NYSE Arca (ARCX).

    GLD est coté sur NYSE Arca. Le calendrier ARCX permet d'intégrer les
    clôtures anticipées (notamment 13:00 America/New_York) au lieu de fixer
    artificiellement toutes les séances à 16:00.
    """
    dates = pd.DatetimeIndex(trading_dates).tz_localize(None).normalize()
    if len(dates) == 0:
        return pd.DataFrame()

    cal = xcals.get_calendar(ARCX_CALENDAR)
    sessions = cal.sessions_in_range(dates.min(), dates.max())

    rows = []
    ny = ZoneInfo("America/New_York")

    for session in sessions:
        close_utc = pd.Timestamp(cal.session_close(session))
        open_utc = pd.Timestamp(cal.session_open(session))
        close_et = close_utc.tz_convert(ny)
        open_et = open_utc.tz_convert(ny)

        rows.append({
            "date": pd.Timestamp(session).tz_localize(None).normalize(),
            "market_open_utc": open_utc,
            "market_close_utc": close_utc,
            "market_open_et": open_et.isoformat(),
            "market_close_et": close_et.isoformat(),
            "is_early_close": bool(
                (close_et.hour, close_et.minute) < (16, 0)
            ),
        })

    schedule = pd.DataFrame(rows).set_index("date").sort_index()
    return schedule.reindex(dates)


def sample_btc_at_arcx_close(
    hourly: pd.DataFrame,
    trading_dates: Iterable[pd.Timestamp],
) -> tuple[pd.Series, pd.DataFrame]:
    """
    Échantillonne Bitcoin exactement à la clôture effective de chaque séance
    NYSE Arca.

    Aucun fallback temporel n'est autorisé. Si la bougie Binance commençant
    exactement à l'heure de clôture est absente, la séance est marquée
    manquante dans l'audit puis exclue de l'échantillon comparatif.
    """
    schedule = build_arcx_close_schedule(trading_dates)
    values: dict[pd.Timestamp, float] = {}
    audit_rows = []

    for d, row in schedule.iterrows():
        close_utc = row.get("market_close_utc")
        calendar_ok = pd.notna(close_utc)
        btc_ok = False
        btc_value = np.nan

        if calendar_ok:
            close_utc = pd.Timestamp(close_utc)
            if close_utc in hourly.index:
                btc_value = float(hourly.loc[close_utc, "open"])
                values[d] = btc_value
                btc_ok = True

        audit_rows.append({
            "date": d,
            "arcx_calendar_session": bool(calendar_ok),
            "market_close_utc": close_utc if calendar_ok else pd.NaT,
            "market_close_et": row.get("market_close_et"),
            "is_early_close": bool(row.get("is_early_close"))
            if calendar_ok else False,
            "btc_exact_close_available": bool(btc_ok),
            "btc_exact_close_price": btc_value,
            "status": (
                "OK"
                if btc_ok
                else ("MISSING_ARCX_SESSION" if not calendar_ok else "MISSING_BTC_EXACT_CLOSE")
            ),
        })

    audit = pd.DataFrame(audit_rows).sort_values("date").reset_index(drop=True)
    btc = pd.Series(values, name="btc_arcx_close").sort_index()
    return btc, audit


def align_ffill(
    s: pd.Series,
    index: pd.DatetimeIndex,
    limit: int | None = None,
) -> pd.Series:
    x = s.copy()
    x.index = pd.to_datetime(x.index).tz_localize(None).normalize()
    x = x[~x.index.duplicated(keep="last")].sort_index()
    return x.reindex(index).ffill(limit=limit)


def log_return(s: pd.Series) -> pd.Series:
    return np.log(s).diff()


def rolling_zscore(s: pd.Series, window: int = 252, min_obs: int = 126) -> pd.Series:
    mu = s.rolling(window, min_periods=min_obs).mean()
    sd = s.rolling(window, min_periods=min_obs).std(ddof=1)
    return (s - mu) / sd.replace(0.0, np.nan)


def map_release_state_to_trading_days(
    release_table: pd.DataFrame,
    trading_idx: pd.DatetimeIndex,
) -> pd.DataFrame:
    events = release_table[
        ["release_date", "cpi_yoy", "inflation_acceleration"]
    ].dropna(subset=["release_date", "cpi_yoy"]).copy()

    events = events.sort_values("release_date")
    daily = pd.DataFrame(index=trading_idx)
    daily.index.name = "date"

    release_yoy = pd.Series(
        events["cpi_yoy"].to_numpy(),
        index=pd.DatetimeIndex(events["release_date"]),
    )
    release_acc = pd.Series(
        events["inflation_acceleration"].to_numpy(),
        index=pd.DatetimeIndex(events["release_date"]),
    )

    daily["inflation_yoy_same_day_available"] = align_ffill(release_yoy, trading_idx)
    daily["inflation_acceleration_same_day_available"] = align_ffill(release_acc, trading_idx)

    # État strictement ex ante pour le rendement close-to-close de la journée t :
    # information disponible à la clôture précédente.
    daily["inflation_yoy_available"] = daily["inflation_yoy_same_day_available"].shift(1)
    daily["inflation_acceleration_available"] = (
        daily["inflation_acceleration_same_day_available"].shift(1)
    )
    return daily


def build_daily_panel(
    cfg: Config,
    outdir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    session = http_session()

    print("[1/7] GLD et Bitcoin...")
    gld = fetch_yahoo_daily("GLD", cfg.start, cfg.end, session)
    trading_idx = pd.DatetimeIndex(gld.index).normalize()

    btc_h = fetch_binance_hourly(cfg.start, cfg.end, session)
    btc, btc_alignment_audit = sample_btc_at_arcx_close(btc_h, trading_idx)
    btc_alignment_audit.to_csv(outdir / "btc_arcx_alignment_audit.csv", index=False)
    btc_alignment_audit.loc[
        ~btc_alignment_audit["btc_exact_close_available"]
    ].to_csv(outdir / "btc_missing_sessions.csv", index=False)

    print("[2/7] Facteurs FRED...")
    fred_cache = outdir / "cache" / "fred"
    fred_start = (pd.Timestamp(cfg.start) - pd.DateOffset(months=24)).date().isoformat()

    fred = {}
    for name, series_id in FRED_SERIES.items():
        fred[name] = fetch_fred(
            series_id,
            session,
            fred_start,
            cfg.end,
            fred_cache,
        )

    print("[3/7] Calendrier CPI BLS point-in-time...")
    bls_calendar = fetch_bls_cpi_calendar(
        start_year=pd.Timestamp(cfg.start).year,
        end_year=pd.Timestamp(cfg.end).year,
        session=session,
        cache_dir=outdir / "cache" / "bls",
    )

    cpi_releases = build_cpi_release_table(
        fred["cpi_nsa"],
        bls_calendar,
        cfg.start,
        cfg.end,
    )
    cpi_releases.to_csv(outdir / "cpi_release_calendar.csv", index=False)

    panel = pd.DataFrame(index=trading_idx)
    panel.index.name = "date"

    panel["gold_px"] = gld["Adj Close"].reindex(trading_idx)
    panel["btc_px"] = btc.reindex(trading_idx)

    panel["sp500"] = align_ffill(fred["sp500"], trading_idx, limit=5)
    panel["real10y"] = align_ffill(fred["real10y"], trading_idx, limit=5)
    panel["usd_broad"] = align_ffill(fred["usd_broad"], trading_idx, limit=5)
    panel["vix"] = align_ffill(fred["vix"], trading_idx, limit=5)
    panel["baa10y"] = align_ffill(fred["baa10y"], trading_idx, limit=5)
    panel["hy_oas_recent"] = align_ffill(fred["hy_oas_recent"], trading_idx, limit=5)
    # NFCI est utilisé uniquement comme classification EX POST.
    # La série historique FRED est révisable et sa date d'observation n'est pas
    # assimilée ici à une date de disponibilité point-in-time.
    panel["nfci_ex_post"] = align_ffill(fred["nfci"], trading_idx, limit=10)

    panel["btc_r"] = log_return(panel["btc_px"])
    panel["gold_r"] = log_return(panel["gold_px"])

    panel["equity"] = log_return(panel["sp500"])
    panel["usd"] = log_return(panel["usd_broad"])
    panel["real_rate"] = panel["real10y"].diff()
    panel["risk_aversion"] = log_return(panel["vix"])
    panel["credit_baa"] = panel["baa10y"].diff()
    panel["hy_oas_recent_change"] = panel["hy_oas_recent"].diff()
    panel["liquidity_stress_ex_post"] = rolling_zscore(
        panel["nfci_ex_post"], 252, 126
    )

    inflation_daily = map_release_state_to_trading_days(cpi_releases, trading_idx)
    panel = panel.join(inflation_daily)

    # Les séances sans prix BTC exactement à la clôture ARCX sont exclues
    # explicitement et restent documentées dans btc_missing_sessions.csv.
    panel = panel.dropna(subset=["btc_px", "gold_px"]).copy()
    panel.to_csv(outdir / "daily_panel.csv")

    metadata = {
        "version": "V4.1.1_GEL",
        "gold_proxy": "GLD adjusted close via Yahoo Finance",
        "btc": (
            "BTCUSDT Binance Spot sampled at the exact NYSE Arca session close "
            "from the ARCX exchange calendar; no temporal fallback"
        ),
        "currency": "USD",
        "core_factors": list(CORE_FACTORS),
        "credit_full_sample_proxy": "BAA10Y",
        "credit_recent_robustness": "BAMLH0A0HYM2",
        "inflation": (
            "CPIAUCNS mapped to actual BLS CPI release dates; "
            "daily state shifted one trading day for strict ex-ante conditioning"
        ),
        "nfci": (
            "EX-POST robustness classification only. Historical FRED NFCI is "
            "revisable and is not treated as point-in-time information."
        ),
        "session_calendar": "exchange_calendars ARCX",
        "fred_series": FRED_SERIES,
    }
    (outdir / "data_metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return panel, cpi_releases, btc_alignment_audit, metadata


# ===========================================================================
# COUVERTURE / CERTIFICATION
# ===========================================================================

def coverage_manifest(panel: pd.DataFrame, outdir: Path) -> pd.DataFrame:
    rows = []

    for c in panel.columns:
        s = panel[c]
        valid = s.notna()
        rows.append({
            "variable": c,
            "n_total": int(len(s)),
            "n_valid": int(valid.sum()),
            "coverage": float(valid.mean()),
            "first_valid": (
                panel.index[valid.argmax()].date().isoformat()
                if valid.any() else None
            ),
            "last_valid": (
                panel.index[np.where(valid.to_numpy())[0][-1]].date().isoformat()
                if valid.any() else None
            ),
        })

    out = pd.DataFrame(rows)
    out.to_csv(outdir / "coverage_manifest.csv", index=False)
    return out


def business_day_distance(a: pd.Timestamp, b: pd.Timestamp) -> int:
    aa = np.datetime64(a.date())
    bb = np.datetime64(b.date())
    if aa <= bb:
        return int(np.busday_count(aa, bb))
    return -int(np.busday_count(bb, aa))


# ===========================================================================
# MULTI-HORIZON
# ===========================================================================

def aggregate_horizon(panel: pd.DataFrame, h: int) -> pd.DataFrame:
    out = pd.DataFrame(index=panel.index)

    out["btc"] = panel["btc_r"].rolling(h).sum()
    out["gold"] = panel["gold_r"].rolling(h).sum()

    out["equity"] = panel["equity"].rolling(h).sum()
    out["usd"] = panel["usd"].rolling(h).sum()
    out["real_rate"] = panel["real10y"].diff(h)
    out["risk_aversion"] = panel["risk_aversion"].rolling(h).sum()
    out["credit_baa"] = panel["baa10y"].diff(h)
    out["hy_oas_recent_change"] = panel["hy_oas_recent"].diff(h)

    for c in [
        "vix", "baa10y", "hy_oas_recent",
        "nfci_ex_post", "liquidity_stress_ex_post",
        "inflation_yoy_available", "inflation_acceleration_available",
    ]:
        if c in panel:
            out[c] = panel[c]

    return out


def winsorize_frame(
    df: pd.DataFrame,
    cols: list[str],
    lo: float,
    hi: float,
) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out:
            continue
        qlo, qhi = out[c].quantile([lo, hi])
        out[c] = out[c].clip(qlo, qhi)
    return out


# ===========================================================================
# RÉGRESSIONS HAC / NEWEY-WEST
# ===========================================================================

def ols_hac(
    y: pd.Series,
    X: pd.DataFrame,
    maxlags: int,
) -> sm.regression.linear_model.RegressionResultsWrapper:
    z = pd.concat([y.rename("y"), X], axis=1).dropna()
    Xc = sm.add_constant(z[X.columns], has_constant="add")
    return sm.OLS(z["y"], Xc).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": maxlags},
    )


def regression_comparison(
    df: pd.DataFrame,
    factors: list[str],
    *,
    horizon: int,
    sample_name: str,
    model_name: str,
    cfg: Config,
    winsor: bool = False,
) -> pd.DataFrame:
    cols = ["btc", "gold"] + factors
    work = df[cols].copy()

    if winsor:
        work = winsorize_frame(
            work,
            cols,
            cfg.winsor_limits[0],
            cfg.winsor_limits[1],
        )

    work = work.dropna()
    if len(work) < cfg.min_regression_obs:
        return pd.DataFrame()

    maxlags = max(5, horizon - 1)
    btc = ols_hac(work["btc"], work[factors], maxlags)
    gold = ols_hac(work["gold"], work[factors], maxlags)
    spread = ols_hac(work["btc"] - work["gold"], work[factors], maxlags)

    rows = []
    for f in factors:
        rows.append({
            "model": model_name,
            "sample": sample_name,
            "horizon": horizon,
            "winsorized": winsor,
            "factor": f,
            "factor_label": FACTOR_LABELS.get(f, f),
            "n": int(len(work)),
            "btc_beta": float(btc.params[f]),
            "btc_se": float(btc.bse[f]),
            "btc_p": float(btc.pvalues[f]),
            "gold_beta": float(gold.params[f]),
            "gold_se": float(gold.bse[f]),
            "gold_p": float(gold.pvalues[f]),
            "delta_beta": float(spread.params[f]),
            "delta_se": float(spread.bse[f]),
            "delta_t": float(spread.tvalues[f]),
            "delta_p": float(spread.pvalues[f]),
            "btc_r2": float(btc.rsquared),
            "gold_r2": float(gold.rsquared),
        })
    return pd.DataFrame(rows)


def joint_wald_spread_test(
    df: pd.DataFrame,
    factors: list[str],
    *,
    horizon: int,
    sample_name: str,
    model_name: str,
    cfg: Config,
    winsor: bool = False,
) -> dict | None:
    """
    Test conjoint :
        H0 : beta_BTC,k = beta_Or,k pour tous les facteurs k.

    Il est estimé directement sur le rendement BTC - or. La statistique de
    Wald utilise la covariance HAC / Newey-West de la régression de spread.
    """
    cols = ["btc", "gold"] + factors
    work = df[cols].copy()

    if winsor:
        work = winsorize_frame(
            work,
            cols,
            cfg.winsor_limits[0],
            cfg.winsor_limits[1],
        )

    work = work.dropna()
    if len(work) < cfg.min_regression_obs:
        return None

    maxlags = max(5, horizon - 1)
    spread = ols_hac(work["btc"] - work["gold"], work[factors], maxlags)

    b = spread.params.loc[factors].to_numpy(dtype=float)
    V = spread.cov_params().loc[factors, factors].to_numpy(dtype=float)
    V_inv = np.linalg.pinv(V)
    stat = float(b.T @ V_inv @ b)
    df_wald = int(len(factors))
    pvalue = float(chi2.sf(stat, df_wald))

    return {
        "model": model_name,
        "sample": sample_name,
        "horizon": horizon,
        "winsorized": winsor,
        "n": int(len(work)),
        "factors": ";".join(factors),
        "wald_chi2": stat,
        "wald_df": df_wald,
        "wald_p": pvalue,
    }


def orthogonalize_risk_aversion(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    z = out[["risk_aversion", "equity"]].dropna()
    if len(z) < 50:
        out["risk_aversion_orth"] = np.nan
        return out

    X = sm.add_constant(z[["equity"]], has_constant="add")
    res = sm.OLS(z["risk_aversion"], X).fit()
    orth = pd.Series(res.resid, index=z.index)
    out["risk_aversion_orth"] = orth.reindex(out.index)
    return out


def run_core_models(
    panel: pd.DataFrame,
    cfg: Config,
    outdir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tables = []
    wald_rows = []

    for h in cfg.horizons:
        hdf = aggregate_horizon(panel, h)

        for winsor in (False, True):
            t = regression_comparison(
                hdf,
                list(CORE_FACTORS),
                horizon=h,
                sample_name="full",
                model_name="core",
                cfg=cfg,
                winsor=winsor,
            )
            if not t.empty:
                tables.append(t)

            w = joint_wald_spread_test(
                hdf,
                list(CORE_FACTORS),
                horizon=h,
                sample_name="full",
                model_name="core",
                cfg=cfg,
                winsor=winsor,
            )
            if w is not None:
                wald_rows.append(w)

        subsamples = {
            "pre_covid": hdf.loc[:pd.Timestamp(cfg.covid_break) - pd.Timedelta(days=1)],
            "post_covid": hdf.loc[pd.Timestamp(cfg.covid_break):],
            "pre_etf": hdf.loc[:pd.Timestamp(cfg.etf_break) - pd.Timedelta(days=1)],
            "post_etf": hdf.loc[pd.Timestamp(cfg.etf_break):],
        }

        for name, sub in subsamples.items():
            t = regression_comparison(
                sub,
                list(CORE_FACTORS),
                horizon=h,
                sample_name=name,
                model_name="core",
                cfg=cfg,
            )
            if not t.empty:
                tables.append(t)

            w = joint_wald_spread_test(
                sub,
                list(CORE_FACTORS),
                horizon=h,
                sample_name=name,
                model_name="core",
                cfg=cfg,
            )
            if w is not None:
                wald_rows.append(w)

        # Extension : VIX orthogonalisé au rendement actions.
        orth = orthogonalize_risk_aversion(hdf)
        ext_factors = list(CORE_FACTORS) + ["risk_aversion_orth"]
        t = regression_comparison(
            orth,
            ext_factors,
            horizon=h,
            sample_name="full",
            model_name="risk_extension",
            cfg=cfg,
        )
        if not t.empty:
            tables.append(t)

    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    wald = pd.DataFrame(wald_rows)

    out.to_csv(outdir / "factor_regressions_v41.csv", index=False)
    wald.to_csv(outdir / "wald_joint_tests_v41.csv", index=False)
    return out, wald


def run_credit_models(panel: pd.DataFrame, cfg: Config, outdir: Path) -> pd.DataFrame:
    tables = []

    for h in cfg.horizons:
        hdf = aggregate_horizon(panel, h)

        # BAA10Y : couverture longue, bloc séparé.
        t = regression_comparison(
            hdf,
            ["credit_baa"],
            horizon=h,
            sample_name="full",
            model_name="credit_baa_standalone",
            cfg=cfg,
        )
        if not t.empty:
            tables.append(t)

        # HY OAS : fenêtre récente uniquement.
        t = regression_comparison(
            hdf,
            ["hy_oas_recent_change"],
            horizon=h,
            sample_name="available_window_only",
            model_name="hy_oas_recent_standalone",
            cfg=cfg,
        )
        if not t.empty:
            tables.append(t)

    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    out.to_csv(outdir / "credit_regressions_isolated.csv", index=False)
    return out


# ===========================================================================
# CONDITIONAL / TAIL
# ===========================================================================

def conditional_quantile_table(
    hdf: pd.DataFrame,
    factor: str,
    q: int,
    horizon: int,
) -> pd.DataFrame:
    x = hdf[["btc", "gold", factor]].dropna().copy()
    if len(x) < q * 25 or x[factor].nunique() < q:
        return pd.DataFrame()

    x["bucket"] = pd.qcut(x[factor], q=q, labels=False, duplicates="drop")
    n_buckets = x["bucket"].nunique()
    if n_buckets != q:
        return pd.DataFrame()

    rows = []
    for bucket, g in x.groupby("bucket", observed=True):
        row = {
            "horizon": horizon,
            "factor": factor,
            "factor_label": FACTOR_LABELS.get(factor, factor),
            "quantile": int(bucket) + 1,
            "n": int(len(g)),
            "factor_min": float(g[factor].min()),
            "factor_median": float(g[factor].median()),
            "factor_max": float(g[factor].max()),
        }
        for a in ["btc", "gold"]:
            r = g[a]
            q05 = r.quantile(0.05)
            row[f"{a}_mean"] = float(r.mean())
            row[f"{a}_median"] = float(r.median())
            row[f"{a}_vol"] = float(r.std(ddof=1))
            row[f"{a}_p05"] = float(q05)
            row[f"{a}_es05"] = float(r[r <= q05].mean())
            row[f"{a}_positive_share"] = float((r > 0).mean())
        row["mean_spread_btc_minus_gold"] = row["btc_mean"] - row["gold_mean"]
        rows.append(row)

    return pd.DataFrame(rows)


def run_conditional_analysis(
    panel: pd.DataFrame,
    cfg: Config,
    outdir: Path,
) -> pd.DataFrame:
    factors = [
        "equity", "usd", "real_rate", "risk_aversion",
        "credit_baa", "liquidity_stress_ex_post",
    ]
    tables = []

    for h in cfg.horizons:
        hdf = aggregate_horizon(panel, h)
        for factor in factors:
            t = conditional_quantile_table(hdf, factor, cfg.quantiles, h)
            if not t.empty:
                tables.append(t)

    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    out.to_csv(outdir / "conditional_quantiles_v4.csv", index=False)
    return out


def moving_block_bootstrap_spread(
    df: pd.DataFrame,
    condition: np.ndarray,
    reps: int,
    block: int,
    seed: int,
) -> tuple[float, float, float]:
    x = df[["btc", "gold"]].to_numpy()
    cond = np.asarray(condition, dtype=bool)

    valid = np.isfinite(x).all(axis=1) & cond
    if valid.sum() < 20:
        return np.nan, np.nan, np.nan

    point = float(np.mean(x[valid, 0] - x[valid, 1]))
    n = len(df)
    rng = np.random.default_rng(seed)
    starts = np.arange(0, max(1, n - block + 1))
    estimates = []

    for _ in range(reps):
        idx: list[int] = []
        while len(idx) < n:
            s = int(rng.choice(starts))
            idx.extend(range(s, min(s + block, n)))
        ii = np.asarray(idx[:n], dtype=int)
        xb = x[ii]
        cb = cond[ii]
        vb = np.isfinite(xb).all(axis=1) & cb
        if vb.sum() >= 10:
            estimates.append(float(np.mean(xb[vb, 0] - xb[vb, 1])))

    if len(estimates) < max(100, reps // 5):
        return point, np.nan, np.nan

    lo, hi = np.quantile(estimates, [0.025, 0.975])
    return point, float(lo), float(hi)


def tail_condition_specs(hdf: pd.DataFrame) -> dict[str, dict]:
    """
    Définitions des queues.

    `direction` indique comment choisir l'observation la plus extrême à
    l'intérieur d'un épisode. Le NFCI est explicitement étiqueté ex post.
    """
    specs: dict[str, dict] = {
        "equity_bottom_10pct": {
            "mask": hdf["equity"] <= hdf["equity"].quantile(0.10),
            "score_col": "equity",
            "direction": "min",
            "classification": "market_observable",
        },
        "equity_bottom_5pct": {
            "mask": hdf["equity"] <= hdf["equity"].quantile(0.05),
            "score_col": "equity",
            "direction": "min",
            "classification": "market_observable",
        },
        "vix_change_top_10pct": {
            "mask": hdf["risk_aversion"] >= hdf["risk_aversion"].quantile(0.90),
            "score_col": "risk_aversion",
            "direction": "max",
            "classification": "market_observable",
        },
        "vix_change_top_5pct": {
            "mask": hdf["risk_aversion"] >= hdf["risk_aversion"].quantile(0.95),
            "score_col": "risk_aversion",
            "direction": "max",
            "classification": "market_observable",
        },
        "vix_level_ge_30": {
            "mask": hdf["vix"] >= 30.0,
            "score_col": "vix",
            "direction": "max",
            "classification": "market_observable",
        },
        "baa_credit_widening_top_10pct": {
            "mask": hdf["credit_baa"] >= hdf["credit_baa"].quantile(0.90),
            "score_col": "credit_baa",
            "direction": "max",
            "classification": "market_observable",
        },
        "baa_credit_widening_top_5pct": {
            "mask": hdf["credit_baa"] >= hdf["credit_baa"].quantile(0.95),
            "score_col": "credit_baa",
            "direction": "max",
            "classification": "market_observable",
        },
        "nfci_ex_post_stress_top_10pct": {
            "mask": (
                hdf["liquidity_stress_ex_post"]
                >= hdf["liquidity_stress_ex_post"].quantile(0.90)
            ),
            "score_col": "liquidity_stress_ex_post",
            "direction": "max",
            "classification": "EX_POST_REVISED_NFCI",
        },
        "dollar_fall_bottom_10pct": {
            "mask": hdf["usd"] <= hdf["usd"].quantile(0.10),
            "score_col": "usd",
            "direction": "min",
            "classification": "market_observable",
        },
        "real_rate_rise_top_10pct": {
            "mask": hdf["real_rate"] >= hdf["real_rate"].quantile(0.90),
            "score_col": "real_rate",
            "direction": "max",
            "classification": "market_observable",
        },
    }

    valid_hy = hdf["hy_oas_recent_change"].dropna()
    if len(valid_hy) >= 250:
        specs["hy_oas_recent_widening_top_10pct"] = {
            "mask": hdf["hy_oas_recent_change"] >= valid_hy.quantile(0.90),
            "score_col": "hy_oas_recent_change",
            "direction": "max",
            "classification": "recent_window_only",
        }

    return specs


def _episode_groups_from_mask(
    base_index: pd.DatetimeIndex,
    mask: pd.Series,
    horizon: int,
) -> list[np.ndarray]:
    """
    Regroupe les observations extrêmes en épisodes.

    Pour h > 1, deux fenêtres dont les dates terminales sont séparées de moins
    de h séances sont fusionnées : leurs rendements h-séances se chevauchent.
    Pour h = 1, les jours extrêmes consécutifs sont regroupés en un même épisode.
    """
    m = mask.reindex(base_index).fillna(False).to_numpy(dtype=bool)
    pos = np.flatnonzero(m)
    if len(pos) == 0:
        return []

    merge_distance = 2 if horizon == 1 else horizon
    groups: list[list[int]] = [[int(pos[0])]]

    for p in pos[1:]:
        p = int(p)
        if p - groups[-1][-1] < merge_distance:
            groups[-1].append(p)
        else:
            groups.append([p])

    return [np.asarray(g, dtype=int) for g in groups]


def build_tail_episodes(
    base: pd.DataFrame,
    condition_name: str,
    spec: dict,
    horizon: int,
) -> pd.DataFrame:
    groups = _episode_groups_from_mask(
        base.index,
        spec["mask"],
        horizon,
    )
    rows = []

    for episode_id, positions in enumerate(groups, start=1):
        g = base.iloc[positions]
        score_col = spec["score_col"]

        valid_score = g[score_col].dropna()
        if valid_score.empty:
            continue

        if spec["direction"] == "min":
            anchor_date = valid_score.idxmin()
        else:
            anchor_date = valid_score.idxmax()

        anchor_pos = int(base.index.get_loc(anchor_date))
        window_start_pos = max(0, anchor_pos - horizon + 1)

        rows.append({
            "horizon": horizon,
            "condition": condition_name,
            "classification": spec["classification"],
            "episode_id": episode_id,
            "episode_start": g.index.min(),
            "episode_end": g.index.max(),
            "condition_days": int(len(g)),
            "anchor_date": anchor_date,
            "anchor_position": anchor_pos,
            "window_start_date": base.index[window_start_pos],
            "window_end_date": anchor_date,
            "condition_value_at_anchor": float(base.loc[anchor_date, score_col]),
            "btc_return": float(base.loc[anchor_date, "btc"]),
            "gold_return": float(base.loc[anchor_date, "gold"]),
            "spread_btc_minus_gold": float(
                base.loc[anchor_date, "btc"] - base.loc[anchor_date, "gold"]
            ),
        })

    return pd.DataFrame(rows)


def bootstrap_episode_mean(
    values: pd.Series,
    reps: int,
    seed: int,
) -> tuple[float, float, float]:
    x = values.dropna().to_numpy(dtype=float)
    if len(x) == 0:
        return np.nan, np.nan, np.nan

    point = float(np.mean(x))
    if len(x) < 5:
        return point, np.nan, np.nan

    rng = np.random.default_rng(seed)
    boots = np.empty(reps, dtype=float)
    for i in range(reps):
        boots[i] = float(np.mean(rng.choice(x, size=len(x), replace=True)))

    lo, hi = np.quantile(boots, [0.025, 0.975])
    return point, float(lo), float(hi)


def summarize_tail_episodes(
    details: pd.DataFrame,
    cfg: Config,
) -> pd.DataFrame:
    if details.empty:
        return pd.DataFrame()

    rows = []
    for (h, condition, classification), g in details.groupby(
        ["horizon", "condition", "classification"],
        observed=True,
    ):
        point, lo, hi = bootstrap_episode_mean(
            g["spread_btc_minus_gold"],
            cfg.bootstrap_reps,
            cfg.random_seed + int(h),
        )

        # Vérification mécanique de non-chevauchement des fenêtres retenues.
        anchors = np.sort(g["anchor_position"].to_numpy(dtype=int))
        if len(anchors) <= 1:
            overlap_free = True
            min_gap = np.nan
        else:
            gaps = np.diff(anchors)
            min_gap = int(gaps.min())
            overlap_free = bool(
                np.all(gaps >= (2 if int(h) == 1 else int(h)))
            )

        rows.append({
            "horizon": int(h),
            "condition": condition,
            "classification": classification,
            "episode_count": int(len(g)),
            "condition_days_total": int(g["condition_days"].sum()),
            "btc_mean_episode_return": float(g["btc_return"].mean()),
            "gold_mean_episode_return": float(g["gold_return"].mean()),
            "btc_median_episode_return": float(g["btc_return"].median()),
            "gold_median_episode_return": float(g["gold_return"].median()),
            "spread_mean_episode": point,
            "spread_ci95_lo": lo,
            "spread_ci95_hi": hi,
            "minimum_anchor_gap_sessions": min_gap,
            "non_overlapping_selected_windows": overlap_free,
        })

    return pd.DataFrame(rows)


def run_tail_analysis(
    panel: pd.DataFrame,
    cfg: Config,
    outdir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Produit trois niveaux :
    1) diagnostics fenêtre-par-fenêtre ;
    2) détail des épisodes indépendants ;
    3) synthèse au niveau des épisodes.

    La synthèse d'épisodes est la sortie destinée à l'interprétation économique.
    """
    window_rows = []
    episode_frames = []

    for h in cfg.horizons:
        hdf = aggregate_horizon(panel, h)
        base = hdf.dropna(subset=["btc", "gold"]).copy()

        for name, spec in tail_condition_specs(base).items():
            cond = spec["mask"].reindex(base.index).fillna(False)
            g = base.loc[cond, ["btc", "gold"]]
            if len(g) < 10:
                continue

            # Diagnostic historique, conservé mais explicitement non indépendant.
            point, lo, hi = moving_block_bootstrap_spread(
                base[["btc", "gold"]],
                cond.to_numpy(),
                cfg.bootstrap_reps,
                cfg.bootstrap_block,
                cfg.random_seed + h,
            )
            window_rows.append({
                "horizon": h,
                "condition": name,
                "classification": spec["classification"],
                "n_overlapping_windows": int(len(g)),
                "btc_mean": float(g["btc"].mean()),
                "gold_mean": float(g["gold"].mean()),
                "spread_mean": point,
                "spread_ci95_lo": lo,
                "spread_ci95_hi": hi,
            })

            episodes = build_tail_episodes(
                base,
                name,
                spec,
                h,
            )
            if not episodes.empty:
                episode_frames.append(episodes)

    window_out = pd.DataFrame(window_rows)
    details = (
        pd.concat(episode_frames, ignore_index=True)
        if episode_frames else pd.DataFrame()
    )
    summary = summarize_tail_episodes(details, cfg)

    window_out.to_csv(
        outdir / "tail_window_diagnostics_v41.csv",
        index=False,
    )
    details.to_csv(
        outdir / "tail_episode_details_v41.csv",
        index=False,
    )
    summary.to_csv(
        outdir / "tail_episode_summary_v41.csv",
        index=False,
    )
    return window_out, details, summary


# ===========================================================================
# INFLATION — ÉTAT + ÉVÉNEMENTS DE PUBLICATION
# ===========================================================================

def next_trading_date(index: pd.DatetimeIndex, d: pd.Timestamp) -> pd.Timestamp | None:
    pos = index.searchsorted(d)
    if pos >= len(index):
        return None
    return index[pos]


def inflation_event_study(
    panel: pd.DataFrame,
    releases: pd.DataFrame,
    outdir: Path,
) -> pd.DataFrame:
    rows = []
    idx = panel.index

    for _, ev in releases.iterrows():
        release_date = pd.Timestamp(ev["release_date"])
        trading_date = next_trading_date(idx, release_date)
        if trading_date is None:
            continue

        # BLS CPI est normalement publié avant la clôture US.
        row = panel.loc[trading_date]
        if pd.isna(row["btc_r"]) or pd.isna(row["gold_r"]):
            continue

        rows.append({
            "reference_month": pd.Timestamp(ev["reference_month"]).date().isoformat(),
            "release_date": release_date.date().isoformat(),
            "trading_date": trading_date.date().isoformat(),
            "cpi_yoy": float(ev["cpi_yoy"]),
            "inflation_acceleration": float(ev["inflation_acceleration"])
            if pd.notna(ev["inflation_acceleration"]) else np.nan,
            "btc_return_release_day": float(row["btc_r"]),
            "gold_return_release_day": float(row["gold_r"]),
        })

    out = pd.DataFrame(rows)
    if not out.empty:
        # Quantiles au niveau des publications, pas au niveau des jours répétés.
        for variable in ["cpi_yoy", "inflation_acceleration"]:
            valid = out[variable].dropna()
            if valid.nunique() >= 5:
                ranks = pd.qcut(valid, q=5, labels=False, duplicates="drop")
                out.loc[valid.index, f"{variable}_quintile"] = ranks.astype(float) + 1.0

    out.to_csv(outdir / "inflation_event_study.csv", index=False)
    return out


def inflation_state_summary(
    panel: pd.DataFrame,
    outdir: Path,
) -> pd.DataFrame:
    x = panel[
        ["btc_r", "gold_r", "inflation_yoy_available"]
    ].dropna().copy()

    if x.empty:
        out = pd.DataFrame()
        out.to_csv(outdir / "inflation_state_summary.csv", index=False)
        return out

    # Seuils calculés sur les valeurs uniques publiées, afin d'éviter de surpondérer
    # mécaniquement un print resté disponible plus longtemps.
    unique_states = pd.Series(
        sorted(x["inflation_yoy_available"].unique()),
        dtype=float,
    )
    q20, q80 = unique_states.quantile([0.20, 0.80])

    states = {
        "low_inflation_state": x["inflation_yoy_available"] <= q20,
        "high_inflation_state": x["inflation_yoy_available"] >= q80,
    }

    rows = []
    for name, mask in states.items():
        g = x.loc[mask]
        rows.append({
            "state": name,
            "threshold_low": float(q20),
            "threshold_high": float(q80),
            "n": int(len(g)),
            "btc_mean": float(g["btc_r"].mean()),
            "gold_mean": float(g["gold_r"].mean()),
            "btc_median": float(g["btc_r"].median()),
            "gold_median": float(g["gold_r"].median()),
            "btc_vol": float(g["btc_r"].std(ddof=1)),
            "gold_vol": float(g["gold_r"].std(ddof=1)),
            "btc_positive_share": float((g["btc_r"] > 0).mean()),
            "gold_positive_share": float((g["gold_r"] > 0).mean()),
        })

    out = pd.DataFrame(rows)
    out.to_csv(outdir / "inflation_state_summary.csv", index=False)
    return out


# ===========================================================================
# STABILITÉ / ROBUSTESSE
# ===========================================================================

def rolling_univariate_beta(
    y: pd.Series,
    x: pd.Series,
    window: int,
    min_obs: int,
) -> pd.Series:
    z = pd.concat([y.rename("y"), x.rename("x")], axis=1)
    cov = z["y"].rolling(window, min_periods=min_obs).cov(z["x"])
    var = z["x"].rolling(window, min_periods=min_obs).var()
    return cov / var.replace(0.0, np.nan)


def run_rolling_betas(
    panel: pd.DataFrame,
    cfg: Config,
    outdir: Path,
) -> pd.DataFrame:
    hdf = aggregate_horizon(panel, 1)
    factors = ["equity", "usd", "real_rate", "risk_aversion", "credit_baa"]
    rows = []

    for f in factors:
        b_btc = rolling_univariate_beta(
            hdf["btc"], hdf[f], cfg.rolling_window, cfg.rolling_min_obs
        )
        b_gold = rolling_univariate_beta(
            hdf["gold"], hdf[f], cfg.rolling_window, cfg.rolling_min_obs
        )
        tmp = pd.DataFrame({
            "date": hdf.index,
            "factor": f,
            "btc_beta": b_btc.to_numpy(),
            "gold_beta": b_gold.to_numpy(),
        })
        tmp["delta_beta"] = tmp["btc_beta"] - tmp["gold_beta"]
        rows.append(tmp)

    out = pd.concat(rows, ignore_index=True)
    out.to_csv(outdir / "rolling_betas_v4.csv", index=False)
    return out


def leave_one_year_out(
    panel: pd.DataFrame,
    cfg: Config,
    outdir: Path,
) -> pd.DataFrame:
    hdf = aggregate_horizon(panel, 1)
    full_n = len(hdf[["btc", "gold"] + list(CORE_FACTORS)].dropna())
    tables = []

    for year in sorted(set(hdf.index.year)):
        sub = hdf[hdf.index.year != year]
        t = regression_comparison(
            sub,
            list(CORE_FACTORS),
            horizon=1,
            sample_name=f"exclude_{year}",
            model_name="core_leave_one_year_out",
            cfg=cfg,
        )
        if not t.empty:
            excluded_n = int((hdf.index.year == year).sum())
            t["excluded_year"] = year
            t["full_core_n"] = full_n
            t["rows_removed_calendar"] = excluded_n
            t["rows_removed_regression"] = full_n - int(t["n"].iloc[0])
            tables.append(t)

    out = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()
    out.to_csv(outdir / "robustness_leave_one_year_out_v4.csv", index=False)
    return out


# ===========================================================================
# CORRÉLATIONS
# ===========================================================================

def correlation_outputs(panel: pd.DataFrame, outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    hdf = aggregate_horizon(panel, 1)
    cols = ["btc", "gold", "equity", "usd", "real_rate", "risk_aversion", "credit_baa"]
    x = hdf[cols].dropna()

    pearson = x.corr(method="pearson")
    spearman = x.corr(method="spearman")
    pearson.to_csv(outdir / "correlation_pearson_v4.csv")
    spearman.to_csv(outdir / "correlation_spearman_v4.csv")
    return pearson, spearman


# ===========================================================================
# FIGURES
# ===========================================================================

def savefig(fig: plt.Figure, path: Path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=190, bbox_inches="tight")
    plt.close(fig)


def plot_normalized(panel: pd.DataFrame, outdir: Path) -> None:
    x = panel[["btc_px", "gold_px"]].dropna()
    n = x / x.iloc[0]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.plot(n.index, n["btc_px"], label="Bitcoin")
    ax.plot(n.index, n["gold_px"], label="Or (GLD)")
    ax.set_yscale("log")
    ax.set_title("Bitcoin et or — capital normalisé à 1")
    ax.set_ylabel("Capital normalisé, échelle logarithmique")
    ax.legend()
    ax.grid(alpha=0.2)
    savefig(fig, outdir / "01_normalized_paths_v4.png")


def plot_rolling_corr(panel: pd.DataFrame, outdir: Path) -> None:
    r = panel[["btc_r", "gold_r"]].dropna()
    corr = r["btc_r"].rolling(90, min_periods=60).corr(r["gold_r"])

    fig, ax = plt.subplots(figsize=(10, 4.8))
    ax.plot(corr.index, corr)
    ax.axhline(0.0, linewidth=1)
    ax.set_ylim(-1, 1)
    ax.set_title("Corrélation roulante 90 observations — Bitcoin / or")
    ax.set_ylabel("Corrélation")
    ax.grid(alpha=0.2)
    savefig(fig, outdir / "02_rolling_corr_90d_v4.png")


def plot_economic_shock_differences(reg: pd.DataFrame, outdir: Path) -> None:
    x = reg[
        (reg["model"] == "core") &
        (reg["sample"] == "full") &
        (reg["horizon"] == 1) &
        (~reg["winsorized"])
    ].copy()

    if x.empty:
        return

    rows = []
    for _, r in x.iterrows():
        f = r["factor"]
        shock = ECONOMIC_SHOCKS[f]
        response = float(r["delta_beta"]) * shock
        se = float(r["delta_se"]) * abs(shock)
        rows.append({
            "label": ECONOMIC_SHOCK_LABELS[f],
            "response": response,
            "lo": response - 1.96 * se,
            "hi": response + 1.96 * se,
        })

    p = pd.DataFrame(rows)
    pos = np.arange(len(p))

    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.errorbar(
        p["response"],
        pos,
        xerr=np.vstack([p["response"] - p["lo"], p["hi"] - p["response"]]),
        fmt="o",
        capsize=3,
    )
    ax.axvline(0.0, linewidth=1)
    ax.set_yticks(pos)
    ax.set_yticklabels(p["label"])
    ax.set_xlabel("Réponse estimée de Bitcoin moins or")
    ax.set_title("Écart de réponse à des chocs économiques comparables — IC 95 %")
    ax.grid(axis="x", alpha=0.2)
    savefig(fig, outdir / "03_economic_shock_differences_v4.png")


def plot_rolling_betas(rolling: pd.DataFrame, outdir: Path) -> None:
    for factor, g in rolling.groupby("factor"):
        fig, ax = plt.subplots(figsize=(10, 4.8))
        ax.plot(g["date"], g["btc_beta"], label="Bitcoin")
        ax.plot(g["date"], g["gold_beta"], label="Or (GLD)")
        ax.axhline(0.0, linewidth=1)
        ax.set_title(f"Bêta roulant 252 observations — {FACTOR_LABELS.get(factor, factor)}")
        ax.set_ylabel("Bêta univarié")
        ax.legend()
        ax.grid(alpha=0.2)
        savefig(fig, outdir / f"rolling_beta_{factor}_v4.png")


def plot_conditional(cond: pd.DataFrame, outdir: Path) -> None:
    x = cond[cond["horizon"] == 1].copy()
    for factor, g in x.groupby("factor"):
        g = g.sort_values("quantile")
        fig, ax = plt.subplots(figsize=(8.5, 4.8))
        ax.plot(g["quantile"], g["btc_mean"], marker="o", label="Bitcoin")
        ax.plot(g["quantile"], g["gold_mean"], marker="o", label="Or (GLD)")
        ax.axhline(0.0, linewidth=1)
        ax.set_xticks(g["quantile"])
        ax.set_xlabel("Quintile du facteur")
        ax.set_ylabel("Rendement logarithmique moyen")
        ax.set_title(f"Analyse conditionnelle — {FACTOR_LABELS.get(factor, factor)}")
        ax.legend()
        ax.grid(alpha=0.2)
        savefig(fig, outdir / f"conditional_{factor}_v4.png")


# ===========================================================================
# VALIDATION V4.1
# ===========================================================================

def validate_v41(
    panel: pd.DataFrame,
    releases: pd.DataFrame,
    coverage: pd.DataFrame,
    core_reg: pd.DataFrame,
    credit_reg: pd.DataFrame,
    loo: pd.DataFrame,
    btc_alignment_audit: pd.DataFrame,
    wald_tests: pd.DataFrame,
    tail_episode_summary: pd.DataFrame,
    cfg: Config,
) -> dict:
    checks: dict[str, object] = {}

    checks["index_unique"] = bool(panel.index.is_unique)
    checks["index_monotonic"] = bool(panel.index.is_monotonic_increasing)
    checks["btc_positive"] = bool((panel["btc_px"] > 0).all())
    checks["gold_positive"] = bool((panel["gold_px"] > 0).all())

    # Alignement exact BTC / NYSE Arca.
    btc_missing = btc_alignment_audit[
        ~btc_alignment_audit["btc_exact_close_available"]
    ].copy()
    early = btc_alignment_audit[
        btc_alignment_audit["is_early_close"]
    ].copy()

    checks["arcx_calendar_session_coverage"] = float(
        btc_alignment_audit["arcx_calendar_session"].mean()
    )
    checks["arcx_calendar_all_gld_dates_pass"] = bool(
        btc_alignment_audit["arcx_calendar_session"].all()
    )
    checks["arcx_early_close_sessions"] = int(len(early))
    checks["arcx_early_close_exact_btc_matches"] = int(
        early["btc_exact_close_available"].sum()
    )
    checks["arcx_early_close_alignment_pass"] = bool(
        early["btc_exact_close_available"].all()
    )
    checks["btc_missing_sessions_count"] = int(len(btc_missing))
    checks["btc_missing_sessions"] = [
        pd.Timestamp(d).date().isoformat()
        for d in btc_missing["date"].tolist()
    ]
    checks["btc_missing_share"] = float(
        len(btc_missing) / max(1, len(btc_alignment_audit))
    )
    checks["btc_missing_sessions_pass"] = bool(
        len(btc_missing) <= BTC_MISSING_SESSION_MAX
        and checks["btc_missing_share"] <= BTC_MISSING_SHARE_MAX
    )

    asset_base = panel[["btc_r", "gold_r"]].dropna()
    core_base = panel[["btc_r", "gold_r"] + list(CORE_FACTORS)].dropna()
    core_ratio = len(core_base) / max(1, len(asset_base))

    checks["asset_return_obs"] = int(len(asset_base))
    checks["core_return_obs"] = int(len(core_base))
    checks["core_sample_coverage_ratio"] = float(core_ratio)
    checks["core_sample_coverage_pass"] = bool(core_ratio >= CORE_MIN_COVERAGE)

    if not core_base.empty:
        start_lag = business_day_distance(asset_base.index.min(), core_base.index.min())
        end_lag = business_day_distance(core_base.index.max(), asset_base.index.max())
    else:
        start_lag = 9999
        end_lag = 9999

    checks["core_start_lag_business_days"] = int(start_lag)
    checks["core_end_lag_business_days"] = int(end_lag)
    checks["core_start_pass"] = bool(start_lag <= CORE_START_MAX_LAG_BDAYS)
    checks["core_end_pass"] = bool(end_lag <= CORE_END_MAX_LAG_BDAYS)

    # Chaque facteur primaire doit avoir une couverture très élevée.
    cov_map = coverage.set_index("variable")["coverage"].to_dict()
    checks["core_factor_coverage"] = {
        f: float(cov_map.get(f, 0.0)) for f in CORE_FACTORS
    }
    checks["core_factor_coverage_pass"] = bool(
        all(float(cov_map.get(f, 0.0)) >= CORE_MIN_COVERAGE for f in CORE_FACTORS)
    )

    # Le HY OAS récent ne doit jamais contaminer le modèle primaire.
    core_factors_used = set(
        core_reg.loc[core_reg["model"] == "core", "factor"].astype(str)
    ) if not core_reg.empty else set()
    checks["forbidden_factor_in_core"] = bool(
        any(f in core_factors_used for f in FORBIDDEN_CORE_FACTORS)
    )
    checks["core_factor_set_exact"] = bool(core_factors_used == set(CORE_FACTORS))

    # Vérification n du modèle full / horizon 1.
    full_core = core_reg[
        (core_reg["model"] == "core") &
        (core_reg["sample"] == "full") &
        (core_reg["horizon"] == 1) &
        (~core_reg["winsorized"])
    ]
    n_reg = int(full_core["n"].iloc[0]) if not full_core.empty else 0
    checks["primary_regression_n"] = n_reg
    checks["primary_regression_n_pass"] = bool(
        n_reg >= CORE_MIN_COVERAGE * max(1, len(asset_base))
    )

    # CPI release calendar.
    checks["cpi_release_count"] = int(len(releases))
    checks["cpi_release_unique_reference_months"] = bool(
        releases["reference_month"].is_unique
    )
    checks["cpi_all_releases_causal"] = bool(
        releases["causal_release"].fillna(False).all()
    )

    # On attend au moins ~9 publications par année moyenne sur la fenêtre.
    years_span = max(1, pd.Timestamp(cfg.end).year - pd.Timestamp(cfg.start).year + 1)
    checks["cpi_minimum_release_count_pass"] = bool(
        len(releases) >= max(80, 9 * years_span)
    )

    # Leave-one-year-out doit retirer de vraies observations.
    if not loo.empty:
        grouped = loo.groupby("excluded_year").first()
        # Une année partielle (2017 commence en août) ne doit pas échouer sur un
        # seuil absolu arbitraire. On exige que l'exclusion retire réellement
        # l'essentiel des observations de calendrier correspondant à cette année.
        required_removed = np.maximum(
            20,
            np.floor(0.50 * grouped["rows_removed_calendar"].to_numpy())
        )
        actual_removed = grouped["rows_removed_regression"].to_numpy()
        checks["loo_all_years_remove_rows"] = bool(
            np.all(actual_removed >= required_removed)
        )
        checks["loo_min_rows_removed"] = int(grouped["rows_removed_regression"].min())
        checks["loo_min_removal_ratio_vs_calendar"] = float(
            np.min(
                grouped["rows_removed_regression"].to_numpy()
                / np.maximum(1, grouped["rows_removed_calendar"].to_numpy())
            )
        )
    else:
        checks["loo_all_years_remove_rows"] = False
        checks["loo_min_rows_removed"] = 0
        checks["loo_min_removal_ratio_vs_calendar"] = 0.0

    # Le bloc HY récent doit rester explicitement isolé.
    if not credit_reg.empty:
        hy_models = credit_reg[credit_reg["model"] == "hy_oas_recent_standalone"]
        checks["hy_recent_isolated"] = bool(
            not hy_models.empty and
            (hy_models["sample"] == "available_window_only").all()
        )
    else:
        checks["hy_recent_isolated"] = False

    # Test de Wald conjoint produit directement par le pipeline.
    primary_wald = wald_tests[
        (wald_tests["model"] == "core") &
        (wald_tests["sample"] == "full") &
        (wald_tests["horizon"] == 1) &
        (~wald_tests["winsorized"])
    ] if not wald_tests.empty else pd.DataFrame()

    checks["primary_joint_wald_present"] = bool(len(primary_wald) == 1)
    if len(primary_wald) == 1:
        wr = primary_wald.iloc[0]
        checks["primary_joint_wald_chi2"] = float(wr["wald_chi2"])
        checks["primary_joint_wald_df"] = int(wr["wald_df"])
        checks["primary_joint_wald_p"] = float(wr["wald_p"])
        checks["primary_joint_wald_finite"] = bool(
            np.isfinite(wr["wald_chi2"]) and np.isfinite(wr["wald_p"])
        )
    else:
        checks["primary_joint_wald_chi2"] = None
        checks["primary_joint_wald_df"] = None
        checks["primary_joint_wald_p"] = None
        checks["primary_joint_wald_finite"] = False

    # NFCI : ex-post uniquement et absent du cœur factoriel.
    checks["nfci_explicitly_ex_post"] = bool(
        "liquidity_stress_ex_post" in panel.columns
        and "nfci_ex_post" in panel.columns
        and "liquidity_stress" not in panel.columns
    )
    checks["nfci_absent_from_core"] = bool(
        "liquidity_stress_ex_post" not in core_factors_used
        and "nfci_ex_post" not in core_factors_used
    )

    # Les observations retenues pour les queues doivent être non chevauchantes
    # au niveau des épisodes.
    if not tail_episode_summary.empty:
        checks["tail_episode_outputs_present"] = True
        checks["tail_selected_windows_non_overlapping"] = bool(
            tail_episode_summary["non_overlapping_selected_windows"].all()
        )
        checks["tail_episode_min_count"] = int(
            tail_episode_summary["episode_count"].min()
        )
    else:
        checks["tail_episode_outputs_present"] = False
        checks["tail_selected_windows_non_overlapping"] = False
        checks["tail_episode_min_count"] = 0

    required = [
        "index_unique",
        "index_monotonic",
        "btc_positive",
        "gold_positive",
        "arcx_calendar_all_gld_dates_pass",
        "arcx_early_close_alignment_pass",
        "btc_missing_sessions_pass",
        "core_sample_coverage_pass",
        "core_start_pass",
        "core_end_pass",
        "core_factor_coverage_pass",
        "core_factor_set_exact",
        "primary_regression_n_pass",
        "cpi_release_unique_reference_months",
        "cpi_all_releases_causal",
        "cpi_minimum_release_count_pass",
        "loo_all_years_remove_rows",
        "hy_recent_isolated",
        "primary_joint_wald_present",
        "primary_joint_wald_finite",
        "nfci_explicitly_ex_post",
        "nfci_absent_from_core",
        "tail_episode_outputs_present",
        "tail_selected_windows_non_overlapping",
    ]

    # forbidden_factor_in_core doit être False.
    checks["pass"] = bool(
        all(bool(checks[k]) for k in required)
        and not bool(checks["forbidden_factor_in_core"])
    )
    return checks


# ===========================================================================
# SYNTHÈSE CERTIFICATION V4.1
# ===========================================================================

def pct(x: float) -> str:
    return "n/a" if pd.isna(x) else f"{100*x:.2f} %"


def write_certification_report(
    checks: dict,
    core_reg: pd.DataFrame,
    credit_reg: pd.DataFrame,
    tail_episode_summary: pd.DataFrame,
    wald_tests: pd.DataFrame,
    inflation_events: pd.DataFrame,
    metadata: dict,
    outdir: Path,
) -> None:
    lines = [
        "# HilmarCorp — Digital Gold V4.1.1 Gel",
        "",
        f"Statut : **{'PASS' if checks['pass'] else 'FAIL'}**",
        "",
        "## Spécification certifiée",
        "",
        "- Cœur factoriel : actions, dollar, taux réel 10 ans.",
        "- VIX : extension orthogonalisée + analyses conditionnelles, hors cœur primaire.",
        "- Crédit : BAA10Y séparé ; HY OAS récent isolé.",
        "- Inflation : CPI NSA associé aux dates effectives de publication BLS.",
        "- Conditionnement inflation quotidien : information disponible à la clôture précédente.",
        "- Bitcoin : prix observé exactement à la clôture effective NYSE Arca, y compris clôtures anticipées.",
        "- NFCI : classification ex post uniquement ; aucune lecture point-in-time.",
        "- Queues : résultats synthétisés par épisodes dont les fenêtres sélectionnées ne se chevauchent pas.",
        "",
        "## Couverture",
        "",
        f"- Observations de rendement actifs : {checks['asset_return_obs']}.",
        f"- Observations cœur factoriel : {checks['core_return_obs']}.",
        f"- Couverture du cœur : {100*checks['core_sample_coverage_ratio']:.2f} %.",
        f"- Début cœur : +{checks['core_start_lag_business_days']} jour(s) ouvré(s).",
        f"- Fin cœur : {checks['core_end_lag_business_days']} jour(s) ouvré(s) avant la dernière observation actifs.",
        "",
        "## Régression primaire — horizon 1 jour",
        "",
    ]

    primary = core_reg[
        (core_reg["model"] == "core") &
        (core_reg["sample"] == "full") &
        (core_reg["horizon"] == 1) &
        (~core_reg["winsorized"])
    ].copy()

    if not primary.empty:
        lines += [
            "| Facteur | β BTC | β or | Δβ BTC-or | p(Δβ=0) |",
            "|---|---:|---:|---:|---:|",
        ]
        for _, r in primary.iterrows():
            lines.append(
                f"| {r['factor_label']} | {r['btc_beta']:.6f} | "
                f"{r['gold_beta']:.6f} | {r['delta_beta']:.6f} | "
                f"{r['delta_p']:.6f} |"
            )

    lines += [
        "",
        "## Test conjoint d'égalité des sensibilités",
        "",
    ]

    primary_wald = wald_tests[
        (wald_tests["model"] == "core") &
        (wald_tests["sample"] == "full") &
        (wald_tests["horizon"] == 1) &
        (~wald_tests["winsorized"])
    ] if not wald_tests.empty else pd.DataFrame()

    if not primary_wald.empty:
        wr = primary_wald.iloc[0]
        lines.append(
            f"- Wald conjoint : χ²({int(wr['wald_df'])}) = "
            f"{wr['wald_chi2']:.4f}, p = {wr['wald_p']:.8g}."
        )

    lines += [
        "",
        "## Alignement BTC / NYSE Arca",
        "",
        f"- Clôtures anticipées détectées : {checks['arcx_early_close_sessions']}.",
        f"- Clôtures anticipées avec prix BTC exact : {checks['arcx_early_close_exact_btc_matches']}.",
        f"- Séances BTC exactes manquantes : {checks['btc_missing_sessions_count']} "
        f"({', '.join(checks['btc_missing_sessions']) if checks['btc_missing_sessions'] else 'aucune'}).",
        "",
        "## Queues par épisodes indépendants",
        "",
    ]

    if not tail_episode_summary.empty:
        for _, r in tail_episode_summary[
            tail_episode_summary["horizon"] == 20
        ].iterrows():
            lines.append(
                f"- {r['condition']} : {int(r['episode_count'])} épisode(s), "
                f"fenêtres non chevauchantes = {bool(r['non_overlapping_selected_windows'])}."
            )

    lines += [
        "",
        "## Crédit isolé",
        "",
    ]

    if not credit_reg.empty:
        for model, g in credit_reg.groupby("model"):
            n = int(g["n"].iloc[0])
            lines.append(f"- {model}: n = {n} sur la fenêtre disponible.")

    lines += [
        "",
        "## Inflation",
        "",
        f"- Publications CPI exploitables : {len(inflation_events)}.",
        "- Aucune surprise d'inflation n'est inférée sans consensus de marché.",
        "- L'accélération mesure la variation du taux d'inflation publié entre deux publications successives.",
        "",
        "## Tests de certification",
        "",
        "```json",
        json.dumps(checks, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Règle de publication",
        "",
        "Un PASS certifie la cohérence de la construction et la couverture annoncée. "
        "Il ne certifie ni une relation causale, ni une performance future.",
    ]

    (outdir / "CERTIFICATION_REPORT.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


# ===========================================================================
# MAIN
# ===========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="HilmarCorp — Digital Gold V4.1.1 Gel"
    )
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument(
        "--end",
        default=pd.Timestamp.now("UTC").date().isoformat(),
    )
    parser.add_argument(
        "--outdir",
        default="reports/digital_gold_v41_gel",
    )
    parser.add_argument("--bootstrap-reps", type=int, default=2000)
    args = parser.parse_args()

    cfg = Config(
        start=args.start,
        end=args.end,
        bootstrap_reps=args.bootstrap_reps,
    )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    print("================================================================")
    print("HILMARCORP — DIGITAL GOLD V4.1.1 GEL")
    print("================================================================")
    print(f"Période demandée : {cfg.start} -> {cfg.end}")
    print(f"Sorties : {outdir.resolve()}")
    print("")

    panel, cpi_releases, btc_alignment_audit, metadata = build_daily_panel(
        cfg, outdir
    )

    print("[4/7] Couverture + régressions cœur / crédit...")
    coverage = coverage_manifest(panel, outdir)
    core_reg, wald_tests = run_core_models(panel, cfg, outdir)
    credit_reg = run_credit_models(panel, cfg, outdir)

    print("[5/7] Analyses conditionnelles / queues / inflation...")
    cond = run_conditional_analysis(panel, cfg, outdir)
    tail_window, tail_episode_details, tail_episode_summary = run_tail_analysis(
        panel, cfg, outdir
    )
    inflation_events = inflation_event_study(panel, cpi_releases, outdir)
    inflation_state = inflation_state_summary(panel, outdir)

    print("[6/7] Stabilité / robustesse / corrélations...")
    rolling = run_rolling_betas(panel, cfg, outdir)
    loo = leave_one_year_out(panel, cfg, outdir)
    pearson, spearman = correlation_outputs(panel, outdir)

    print("[7/7] Figures + certification...")
    plot_normalized(panel, outdir)
    plot_rolling_corr(panel, outdir)
    plot_economic_shock_differences(core_reg, outdir)
    plot_rolling_betas(rolling, outdir)
    plot_conditional(cond, outdir)

    checks = validate_v41(
        panel,
        cpi_releases,
        coverage,
        core_reg,
        credit_reg,
        loo,
        btc_alignment_audit,
        wald_tests,
        tail_episode_summary,
        cfg,
    )

    (outdir / "validation_v41.json").write_text(
        json.dumps(checks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    diagnostics = {
        "version": "V4.1.1_GEL",
        "config": asdict(cfg),
        "pearson_btc_gold": (
            float(pearson.loc["btc", "gold"])
            if "btc" in pearson.index and "gold" in pearson.columns
            else None
        ),
        "spearman_btc_gold": (
            float(spearman.loc["btc", "gold"])
            if "btc" in spearman.index and "gold" in spearman.columns
            else None
        ),
        "metadata": metadata,
    }
    (outdir / "diagnostics_v41.json").write_text(
        json.dumps(diagnostics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    write_certification_report(
        checks,
        core_reg,
        credit_reg,
        tail_episode_summary,
        wald_tests,
        inflation_events,
        metadata,
        outdir,
    )

    print("")
    print("================================================================")
    print("PASS_V4_1_1_GEL" if checks["pass"] else "FAIL_V4_1_1_GEL")
    print("================================================================")
    print(json.dumps(checks, indent=2, ensure_ascii=False))
    print("")
    print("Artefacts critiques :")
    for name in [
        "btc_arcx_alignment_audit.csv",
        "btc_missing_sessions.csv",
        "coverage_manifest.csv",
        "cpi_release_calendar.csv",
        "factor_regressions_v41.csv",
        "wald_joint_tests_v41.csv",
        "credit_regressions_isolated.csv",
        "conditional_quantiles_v4.csv",
        "tail_window_diagnostics_v41.csv",
        "tail_episode_details_v41.csv",
        "tail_episode_summary_v41.csv",
        "inflation_event_study.csv",
        "inflation_state_summary.csv",
        "rolling_betas_v4.csv",
        "robustness_leave_one_year_out_v4.csv",
        "validation_v41.json",
        "CERTIFICATION_REPORT.md",
        "03_economic_shock_differences_v4.png",
    ]:
        print(f" - {outdir / name}")

    if not checks["pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
