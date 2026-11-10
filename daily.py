#!/usr/bin/env python3
"""
daily.py — personal daily dashboard

Shows:
  • Indian and US market indices / tracked holdings
  • Portfolio distance from purchase price
  • Brent crude and 24K gold (10 g)
  • US Federal Funds rate
  • Weather and air quality for selected cities
  • Currency rates against INR
  • GDP per capita and world ranking
  • Optional top market movers (--movers)

macOS / Windows / Linux compatible. Requires Python 3.9+ and requests.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

NAME = "Pranav"

# India has no daylight-saving time. This fixed offset is correct year-round.
IST = timezone(timedelta(hours=5, minutes=30), "IST")

CITIES = [
    {"name": "Bengaluru", "lat": 12.9716, "lon": 77.5946},
    {"name": "Lucknow", "lat": 26.8467, "lon": 80.9462},
    {"name": "Kamloops", "lat": 50.6745, "lon": -120.3273},
    {"name": "Gurugram", "lat": 28.4601, "lon": 77.0262},
    {"name": "Amsterdam", "lat": 52.3676, "lon": 4.9041},
    {"name": "Stockholm", "lat": 59.3293, "lon": 18.0686},
]

# "buy" is optional. Add it to a holding to show its purchase price and
# distance from break-even in the Markets section.
US_INDICES = [
    {"name": "S&P 500", "symbol": "%5EGSPC"},
    {"name": "DJIA", "symbol": "%5EDJI"},
    {"name": "Nasdaq Composite", "symbol": "%5EIXIC"},
]

INDIA_INDICES = [
    {"name": "Nifty 50", "symbol": "%5ENSEI"},
    {"name": "Sensex", "symbol": "%5EBSESN"},
]

# Quantities and purchase prices supplied by you.
US_HOLDINGS = [
    {"name": "BRK-B", "symbol": "BRK-B", "buy": 497.96, "qty": 0.1998},
    {"name": "Accenture", "symbol": "ACN", "buy": 255.63, "qty": 7},
]

INDIA_HOLDINGS = [
    {"name": "GoldBees", "symbol": "GOLDBEES.NS", "buy": 106.70, "qty": 1},
    # Jio Platforms
    {"name": "JPL (Jio)", "symbol": "JPL.NS", "buy": 1119.00, "qty": 24},
    {"name": "HDFC Bank", "symbol": "HDFCBANK.NS", "buy": 810.00, "qty": 246},
    {"name": "HINDUNILVR", "symbol": "HINDUNILVR.NS", "buy": 2108.48, "qty": 98},
    {"name": "ITC", "symbol": "ITC.NS", "buy": 309.00, "qty": 647},
    {"name": "DMart", "symbol": "DMART.NS", "buy": 4090.35, "qty": 158},
    {"name": "TCS", "symbol": "TCS.NS", "buy": 3081.04, "qty": 2568},
]

CURRENCY_PAIRS = [
    {"name": "USD -> INR", "symbol": "USDINR=X"},
    {"name": "EUR -> INR", "symbol": "EURINR=X"},
    {"name": "GBP -> INR", "symbol": "GBPINR=X"},
    {"name": "CAD -> INR", "symbol": "CADINR=X"},
    {"name": "AUD -> INR", "symbol": "AUDINR=X"},
    {"name": "SEK -> INR", "symbol": "SEKINR=X"},
    {"name": "JPY -> INR", "symbol": "JPYINR=X"},
]

NSE_SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS",
    "KOTAKBANK.NS", "HINDUNILVR.NS", "SBIN.NS", "BAJFINANCE.NS", "WIPRO.NS",
    "AXISBANK.NS", "MARUTI.NS", "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS",
    "NESTLEIND.NS", "POWERGRID.NS", "NTPC.NS", "ONGC.NS", "TATAMOTORS.NS",
]

NYSE_SYMBOLS = [
    "JPM", "BAC", "WFC", "GS", "MS", "C", "BRK-B", "XOM", "CVX", "BA",
    "GE", "PFE", "JNJ", "KO", "WMT", "PG", "T", "VZ", "IBM", "UPS",
]

NASDAQ_SYMBOLS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO",
    "COST", "NFLX", "AMD", "INTC", "QCOM", "TXN", "ADBE", "ACN",
    "MU", "AMAT", "LRCX", "PANW",
]

# World Bank 3-letter codes. GDP per capita is updated annually.
GDP_COUNTRIES = [
    "USA", "CAN", "NLD", "SWE", "NOR", "FIN", "DNK", "AUS", "JPN", "NZL",
    "GBR", "IND", "IRL", "FRA", "ESP", "ITA", "LVA", "LTU", "EST", "CHN",
]

TROY_OZ_PER_GRAM = 1 / 31.1035

# Keep the cache beside this script. This works on macOS and Windows and
# avoids depending on the current working directory.
SCRIPT_DIR = Path(__file__).resolve().parent
GDP_CACHE = SCRIPT_DIR / "gdp_cache.json"
GDP_CACHE_DAYS = 30
GDP_CACHE_VERSION = 2

WB_AGGREGATES = {
    "WLD", "EUU", "EMU", "ARB", "CSS", "CEB", "EAR", "EAS", "EAP", "TEA",
    "ECS", "ECA", "TEC", "FCS", "HPC", "HIC", "IBD", "IBT", "IDB", "IDX",
    "IDA", "LTE", "LCN", "LAC", "TLA", "LDC", "LMY", "LIC", "LMC", "MEA",
    "MNA", "TMN", "MIC", "NAC", "INX", "OED", "OSS", "PSS", "PST", "PRE",
    "SST", "SAS", "TSA", "SSF", "SSA", "TSS", "UMC", "AFE", "AFW",
}

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; daily.py/1.0)"}
HTTP = requests.Session()
HTTP.headers.update(HEADERS)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def line(char="=", width=60):
    print(char * width)


def header(text):
    print(f"\n{text}")
    line("-", 60)


def yahoo_chart(symbol, timeout=8):
    """Return Yahoo Finance chart metadata, or raise an exception."""
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?interval=1d&range=1d"
    )
    response = HTTP.get(url, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    result = payload["chart"]["result"]
    if not result:
        raise ValueError(f"No Yahoo Finance result for {symbol}")
    return result[0]["meta"]


# ---------------------------------------------------------------------------
# Weather
# ---------------------------------------------------------------------------

def fetch_weather(city):
    """Return current temperature for one city, or an error if unavailable."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "current": "temperature_2m",
        "timezone": "auto",
    }

    last_error = "Unknown error"
    for attempt in range(2):
        try:
            response = HTTP.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()

            # Open-Meteo can return an explanatory error payload with HTTP 200.
            if data.get("error"):
                raise ValueError(data.get("reason", "Open-Meteo API error"))

            current = data.get("current") or {}
            temp = current.get("temperature_2m")
            if temp is None:
                raise ValueError("Response did not contain current.temperature_2m")

            return {
                "name": city["name"],
                "temp": round(float(temp), 1),
                "error": None,
            }
        except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt == 0:
                time.sleep(1)

    return {"name": city["name"], "temp": None, "error": last_error}


def show_weather():
    """Temperature only, coldest city first; show the reason for failures."""
    results = [fetch_weather(city) for city in CITIES]
    found = sorted(
        (x for x in results if x["temp"] is not None),
        key=lambda x: x["temp"],
    )
    failed = [x for x in results if x["temp"] is None]

    for row in found:
        print(f"  {row['name']:<12} {row['temp']:>5.1f}°C")

    if failed:
        print("  Could not fetch:")
        for row in failed:
            print(f"    {row['name']}: {row['error']}")


# ---------------------------------------------------------------------------
# Air quality
# ---------------------------------------------------------------------------

def fetch_aqi(city):
    """Return current US AQI and PM2.5 for one city, or None."""
    try:
        url = (
            "https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={city['lat']}&longitude={city['lon']}"
            "&current=us_aqi,pm2_5"
        )
        response = HTTP.get(url, timeout=8)
        response.raise_for_status()
        current = response.json()["current"]
        aqi = int(current["us_aqi"])
        pm25 = round(float(current["pm2_5"]), 1)

        if aqi <= 50:
            label = "Good"
        elif aqi <= 100:
            label = "Moderate"
        elif aqi <= 150:
            label = "Unhealthy for sensitive"
        elif aqi <= 200:
            label = "Unhealthy"
        elif aqi <= 300:
            label = "Very Unhealthy"
        else:
            label = "Hazardous"

        return {
            "name": city["name"], "aqi": aqi, "pm25": pm25, "label": label
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def show_aqi():
    """Cleanest air first."""
    results = [fetch_aqi(city) for city in CITIES]
    found = sorted((x for x in results if x is not None), key=lambda x: x["aqi"])
    for row in found:
        print(
            f"  {row['name']:<12} AQI: {row['aqi']:>3}  "
            f"PM2.5: {row['pm25']:>5.1f}  ({row['label']})"
        )
    missing = len(results) - len(found)
    if missing:
        print(f"  ({missing} city/cities could not be fetched)")


# ---------------------------------------------------------------------------
# Currency
# ---------------------------------------------------------------------------

def get_usd_inr():
    """Fetch live USD->INR rate; return float or None on failure."""
    try:
        meta = yahoo_chart("USDINR=X", timeout=8)
        return float(meta["regularMarketPrice"])
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def fetch_currency(pair):
    """Return how many rupees one unit of the other currency costs, or None."""
    try:
        meta = yahoo_chart(pair["symbol"])
        price = float(meta["regularMarketPrice"])
        prev = float(meta.get("chartPreviousClose", price))
        if prev == 0:
            raise ValueError("Previous close is zero")
        return {
            "name": pair["name"],
            "price": price,
            "change": round(price - prev, 4),
            "pct": round((price - prev) / prev * 100, 2),
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def show_currency():
    """Fewest rupees per unit first, i.e. where the rupee buys the most."""
    results = [fetch_currency(pair) for pair in CURRENCY_PAIRS]
    found = sorted((x for x in results if x is not None), key=lambda x: x["price"])
    for row in found:
        change = f"{row['change']:+.4f} ({row['pct']:+.2f}%)"
        print(f"  {row['name']:<12} Rs.{row['price']:>9,.4f}  {change:>20}")
    missing = len(results) - len(found)
    if missing:
        print(f"  ({missing} pair(s) could not be fetched)")


# ---------------------------------------------------------------------------
# Markets and portfolio
# ---------------------------------------------------------------------------

def fetch_quote(stock):
    """Fetch a quote and compare it with the configured purchase price."""
    try:
        meta = yahoo_chart(stock["symbol"])
        price = float(meta["regularMarketPrice"])
        prev = float(meta.get("chartPreviousClose", price))
        if prev == 0:
            raise ValueError("Previous close is zero")

        buy = stock.get("buy")
        if buy is None:
            performance = None
            performance_label = None
        elif price >= buy:
            performance = (price - buy) / buy * 100 if buy else None
            performance_label = "PROFIT"
        else:
            # Percentage rise required from the current price to reach buy price.
            performance = (buy - price) / price * 100 if price else None
            performance_label = "TO BREAKEVEN"

        return {
            "name": stock["name"],
            "symbol": stock["symbol"],
            "price": price,
            "change": round(price - prev, 2),
            "pct": round((price - prev) / prev * 100, 2),
            "buy": buy,
            "performance": performance,
            "performance_label": performance_label,
        }
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None

def format_indian_number(value, decimals=2, signed=False):
    """Format numbers using Indian digit grouping, e.g. 1,23,456.78."""
    number = float(value)
    sign = ""
    if number < 0:
        sign = "-"
    elif signed and number > 0:
        sign = "+"
    number = abs(number)

    whole, fraction = f"{number:.{decimals}f}".split(".")
    if len(whole) > 3:
        last_three = whole[-3:]
        remaining = whole[:-3]
        groups = []
        while remaining:
            groups.insert(0, remaining[-2:])
            remaining = remaining[:-2]
        whole = ",".join(groups + [last_three])

    return f"{sign}{whole}.{fraction}"


def format_market_number(value, currency, signed=False):
    """Use Indian grouping for INR rows and standard grouping for USD rows."""
    if currency == "Rs.":
        return format_indian_number(value, signed=signed)
    return f"{value:+,.2f}" if signed else f"{value:,.2f}"


def print_market_group(title, stocks, currency):
    """Print prices, daily moves, buy prices and profit/breakeven percentages."""
    print()
    print(f"  {title}")
    print(
        f"  {'NAME':<18} {'PRICE':>13} {'DAY CHANGE':>21} "
        f"{'BUY':>13} {'PROFIT % / TO BREAKEVEN':>25}"
    )

    for stock in stocks:
        quote = fetch_quote(stock)
        if quote is None:
            print(f"  {stock['name']:<18} Could not fetch")
            continue

        price_text = format_market_number(quote["price"], currency)
        change_amount = format_market_number(quote["change"], currency, signed=True)
        change = f"{change_amount} ({quote['pct']:+.2f}%)"
        buy_text = (
            format_market_number(quote["buy"], currency)
            if quote["buy"] is not None else "-"
        )
        if quote["performance"] is None:
            performance_text = "-"
        else:
            performance_text = (
                f"{quote['performance_label']} "
                f"{quote['performance']:.2f}%"
            )

        print(
            f"  {quote['name']:<18} {price_text:>13} "
            f"{change:>21} {buy_text:>13} {performance_text:>25}"
        )



# ---------------------------------------------------------------------------
# Commodities
# ---------------------------------------------------------------------------

def get_crude_oil_inr(usd_inr):
    """
    Fetch Brent crude oil price (USD/barrel) via Yahoo Finance (BZ=F),
    then convert to INR per barrel. One barrel is about 158.987 litres.
    """
    try:
        meta = yahoo_chart("BZ=F")
        price_usd = float(meta["regularMarketPrice"])
        prev_usd = float(meta.get("chartPreviousClose", price_usd))
        change_usd = round(price_usd - prev_usd, 2)
        pct = round((change_usd / prev_usd) * 100, 2) if prev_usd else 0
        arrow = "+" if change_usd >= 0 else ""

        if usd_inr:
            price_inr = round(price_usd * usd_inr, 2)
            inr_str = f" (Rs.{price_inr:,.2f}/barrel)"
        else:
            inr_str = " (INR conversion unavailable)"

        print(
            f"  {'Brent Crude':<18} ${price_usd:>8,.2f}/bbl  "
            f"{arrow}{change_usd:.2f} ({arrow}{pct}%)"
            f"{inr_str}"
        )
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"  {'Brent Crude':<18} Could not fetch ({exc})")


def get_gold_inr(usd_inr):
    """
    Fetch gold spot price (USD/troy oz) via Yahoo Finance (GC=F),
    convert to INR per 10 grams of 24K gold.
    1 troy oz = 31.1035 g.
    """
    try:
        meta = yahoo_chart("GC=F")
        price_usd_oz = float(meta["regularMarketPrice"])
        prev_usd_oz = float(meta.get("chartPreviousClose", price_usd_oz))
        change_oz = price_usd_oz - prev_usd_oz
        pct = round((change_oz / prev_usd_oz) * 100, 2) if prev_usd_oz else 0
        arrow = "+" if change_oz >= 0 else ""

        factor_10g = 10 * TROY_OZ_PER_GRAM
        if usd_inr:
            price_inr_10g = round(price_usd_oz * factor_10g * usd_inr, 2)
            change_inr_10g = round(change_oz * factor_10g * usd_inr, 2)
            c_arrow = "+" if change_inr_10g >= 0 else ""
            print(
                f"  {'Gold 24kt (10 g)':<18} Rs.{price_inr_10g:>9,.2f}  "
                f"{c_arrow}{change_inr_10g:,.2f} ({arrow}{pct}%)"
            )
        else:
            price_usd_10g = round(price_usd_oz * factor_10g, 2)
            print(
                f"  {'Gold 24kt (10 g)':<18} ${price_usd_10g:>7,.2f}/10g  "
                f"{arrow}{round(change_oz * factor_10g, 2):,.2f} "
                f"({arrow}{pct}%) (INR conversion unavailable)"
            )
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        print(f"  {'Gold 24kt (10 g)':<18} Could not fetch ({exc})")


# ---------------------------------------------------------------------------
# US Federal Funds rate
# ---------------------------------------------------------------------------

def get_fed_rate():
    """
    Fetch the latest US Federal Funds Rate observation.
    Primary: US Treasury FiscalData API.
    Fallback: Federal Reserve H.15 release.
    Last resort: Yahoo Finance 13-week T-bill proxy (^IRX).
    """
    # Primary: US Treasury FiscalData API (no key required).
    try:
        url = (
            "https://api.fiscaldata.treasury.gov/services/api/v1/"
            "accounting/od/avg_interest_rates"
            "?fields=record_date,security_desc,avg_interest_rate_amt"
            "&filter=security_desc:eq:Federal%20Funds%20Rate"
            "&sort=-record_date&page[size]=1"
        )
        response = HTTP.get(url, timeout=10)
        response.raise_for_status()
        record = response.json()["data"][0]
        rate = float(record["avg_interest_rate_amt"])
        date_str = record["record_date"]
        print(
            f"  {'US Fed Rate':<18} {rate:.2f}%  "
            f"(effective rate as of {date_str})"
        )
        return
    except Exception:
        pass

    # Fallback: Federal Reserve H.15 release HTML.
    try:
        url = "https://www.federalreserve.gov/releases/h15/current/default.htm"
        response = HTTP.get(url, timeout=10)
        response.raise_for_status()
        match = re.search(
            r"Federal Funds.*?<td[^>]*>([\d.]+)</td>",
            response.text,
            re.IGNORECASE | re.DOTALL,
        )
        if match:
            rate = float(match.group(1))
            print(f"  {'US Fed Rate':<18} {rate:.2f}% (Fed H.15 release)")
            return
    except Exception:
        pass

    # Last resort: Yahoo Finance ^IRX (13-week T-bill as a proxy).
    try:
        meta = yahoo_chart("%5EIRX")
        rate = float(meta["regularMarketPrice"])
        print(f"  {'US Fed Rate':<18} ~{rate:.2f}% (13-week T-bill proxy)")
    except Exception as exc:
        print(f"  {'US Fed Rate':<18} Could not fetch ({exc})")


# ---------------------------------------------------------------------------
# Optional top market movers
# ---------------------------------------------------------------------------

def fetch_price_change(symbol):
    try:
        meta = yahoo_chart(symbol)
        price = float(meta["regularMarketPrice"])
        prev = float(meta.get("chartPreviousClose", price))
        if prev == 0:
            return None
        pct = round((price - prev) / prev * 100, 2)
        return symbol, price, pct
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None


def get_top_movers_nse():
    results = []
    for symbol in NSE_SYMBOLS:
        data = fetch_price_change(symbol)
        if data:
            results.append(data)
    if not results:
        print("  Could not fetch NSE movers.")
        return

    gainer = max(results, key=lambda x: x[2])
    loser = min(results, key=lambda x: x[2])
    g_arrow = "+" if gainer[2] >= 0 else ""
    l_arrow = "+" if loser[2] >= 0 else ""
    print(
        f"  {'NSE Top Gainer':<18} {gainer[0].replace('.NS', ''):<14} "
        f"{gainer[1]:>10,.2f}  {g_arrow}{gainer[2]}%"
    )
    print(
        f"  {'NSE Top Loser':<18} {loser[0].replace('.NS', ''):<14} "
        f"{loser[1]:>10,.2f}  {l_arrow}{loser[2]}%"
    )


def get_top_movers_us(exchange_label, symbols):
    results = []
    for symbol in symbols:
        data = fetch_price_change(symbol)
        if data:
            results.append(data)
    if not results:
        print(f"  Could not fetch {exchange_label} movers.")
        return

    gainer = max(results, key=lambda x: x[2])
    loser = min(results, key=lambda x: x[2])
    g_arrow = "+" if gainer[2] >= 0 else ""
    l_arrow = "+" if loser[2] >= 0 else ""
    print(
        f"  {exchange_label} Top Gainer: {gainer[0]:<8} "
        f"${gainer[1]:>10,.2f}  {g_arrow}{gainer[2]}%"
    )
    print(
        f"  {exchange_label} Top Loser:  {loser[0]:<8} "
        f"${loser[1]:>10,.2f}  {l_arrow}{loser[2]}%"
    )


# ---------------------------------------------------------------------------
# GDP per capita (World Bank)
# ---------------------------------------------------------------------------

def read_gdp_cache():
    """Read saved figures and their age in days, or (None, None)."""
    try:
        with GDP_CACHE.open("r", encoding="utf-8") as handle:
            saved = json.load(handle)
        if saved.get("version") != GDP_CACHE_VERSION:
            return None, None
        if sorted(saved.get("countries", [])) != sorted(GDP_COUNTRIES):
            return None, None
        age = (time.time() - saved["fetched"]) / 86400
        return saved, age
    except (OSError, ValueError, KeyError, TypeError):
        return None, None


def fetch_gdp_rows():
    """Fetch every country's GDP per capita for a world ranking."""
    url = (
        "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.PCAP.CD"
        "?format=json&mrnev=1&per_page=500"
    )
    records = None

    # The API can be slow on the first hit, so allow plenty of time and retry.
    for timeout in (25, 40):
        try:
            response = HTTP.get(url, timeout=timeout)
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, list) and len(payload) > 1 and payload[1]:
                records = payload[1]
                break
        except Exception:
            continue

    if not records:
        return None

    world = []
    for item in records:
        code = item.get("countryiso3code") or ""
        value = item.get("value")
        if value is None or not code or code in WB_AGGREGATES:
            continue
        world.append({
            "code": code,
            "name": item["country"]["value"],
            "value": float(value),
            "year": item.get("date", ""),
        })

    # Rank every country, richest first, then keep only the countries listed.
    world.sort(key=lambda x: -x["value"])
    for position, entry in enumerate(world, start=1):
        entry["rank"] = position

    saved = {
        "version": GDP_CACHE_VERSION,
        "fetched": time.time(),
        "countries": GDP_COUNTRIES,
        "world_size": len(world),
        "rows": [e for e in world if e["code"] in GDP_COUNTRIES],
    }
    try:
        with GDP_CACHE.open("w", encoding="utf-8") as handle:
            json.dump(saved, handle)
    except OSError:
        pass  # A read-only folder should not break the dashboard.
    return saved


def show_gdp_per_capita():
    """GDP per capita in current US dollars, with each country's world rank."""
    saved, age = read_gdp_cache()
    if saved is None or age > GDP_CACHE_DAYS:
        fresh = fetch_gdp_rows()
        if fresh:
            saved, age = fresh, 0.0
        elif saved is None:
            print("  Could not reach the World Bank API, and nothing is cached yet.")
            print("  It is often slow — try again in a minute.")
            return
        # Otherwise keep the stale cache rather than showing nothing.

    rows = sorted(saved["rows"], key=lambda x: -x["value"])
    total = saved.get("world_size", 0)

    print(f"  {'#':>3} {'COUNTRY':<24} {'GDP/CAPITA':>12} {'YEAR':>6} {'WORLD':>6}")
    for i, row in enumerate(rows, start=1):
        amount = "$" + format(row["value"], ",.0f")
        print(
            f"  {i:>2}. {row['name']:<24} {amount:>12} "
            f"{row['year']:>6} {'#' + str(row['rank']):>6}"
        )

    if total:
        print(f"  World rank is out of {total} countries with data.")
    absent = [c for c in GDP_COUNTRIES if c not in [r["code"] for r in rows]]
    if absent:
        print(f"  (no figure returned for: {', '.join(absent)})")
    if len({row["year"] for row in rows if row["year"]}) > 1:
        print("  Note: not every country reports for the same year.")
    if age and age >= 1:
        print(f"  (cached figures, {age:.0f} days old)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    now_local = datetime.now().astimezone()
    now_ist = now_local.astimezone(IST)

    day_str = now_ist.strftime("%a, %d %b %Y")
    time_str = now_ist.strftime("%I:%M %p").lstrip("0")

    # Greet on the clock you are actually living by, not on IST.
    hour = now_local.hour
    greeting = (
        "Good morning" if hour < 12
        else "Good afternoon" if hour < 17
        else "Good evening"
    )

    line("=", 60)
    print(f"\n{greeting}, {NAME}!")
    print(f"{day_str} | {time_str} IST")

    # Only print a second clock when you are not in India.
    if now_local.utcoffset() != now_ist.utcoffset():
        local_zone = now_local.tzname() or "local"
        local_time = now_local.strftime("%I:%M %p").lstrip("0")
        local_day = now_local.strftime("%a, %d %b")
        print(f"Local: {local_time} {local_zone}, {local_day}")

    print()
    line("=", 60)

    show_markets()

    # Fetch USD->INR once; reuse for the commodity conversions below.
    usd_inr = get_usd_inr()

    header("COMMODITIES & RATES")
    get_crude_oil_inr(usd_inr)
    get_gold_inr(usd_inr)
    get_fed_rate()

    header("WEATHER (coldest first)")
    show_weather()

    header("AIR QUALITY INDEX (cleanest first)")
    show_aqi()

    header("CURRENCY RATES (rupee strongest first)")
    show_currency()

    header("GDP PER CAPITA (US$, highest first)")
    show_gdp_per_capita()

    # Top movers are off by default: this costs many separate requests.
    # Run `python3 daily.py --movers` when you want them.
    if "--movers" in sys.argv:
        print()
        line("=", 60)
        print("TOP MOVERS")
        line("-", 60)
        get_top_movers_nse()
        get_top_movers_us("NYSE", NYSE_SYMBOLS)
        get_top_movers_us("Nasdaq", NASDAQ_SYMBOLS)

    print()
    line("=", 60)
    print()


if __name__ == "__main__":
    main()
