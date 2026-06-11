#!/usr/bin/env python3
"""
scrape_events.py — LeaveWithDad event aggregator
Scrapes upcoming events from:
  - City of Plantation (plantation.org)
  - City of Pembroke Pines (ppines.com)
  - City of Weston (westonfl.org)

Outputs: events.json at the site root

Usage:
  pip install requests beautifulsoup4
  python3 scripts/scrape_events.py

Cron (daily at 6am, run from site root):
  0 6 * * * cd /path/to/leavewithdad && python3 scripts/scrape_events.py

Sources not yet included (JS-rendered, need Playwright or manual curation):
  - visitlauderdale.com  (SimpleView CMS, JS-rendered)
  - broward.org          (SharePoint, JS-rendered / blocked)
"""

import json
import re
import hashlib
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Run: pip3 install beautifulsoup4")
    sys.exit(1)

try:
    from curl_cffi import requests
    SESSION = requests.Session(impersonate="chrome120")
    print("  (using curl_cffi — Chrome TLS fingerprint)")
except ImportError:
    try:
        import requests
        SESSION = requests.Session()
        print("  (using requests — install curl_cffi for better compatibility)")
    except ImportError:
        print("ERROR: Run: pip3 install curl-cffi beautifulsoup4")
        sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_FILE = Path(__file__).parent.parent / "events.json"
TODAY       = date.today()
CUTOFF_DAYS = 120          # scrape events up to N days ahead
HEADERS = {
    "User-Agent":                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Accept-Language":           "en-US,en;q=0.9",
    "Accept-Encoding":           "gzip, deflate, br",
    "Connection":                "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest":            "document",
    "Sec-Fetch-Mode":            "navigate",
    "Sec-Fetch-Site":            "none",
    "Sec-Fetch-User":            "?1",
    "Cache-Control":             "max-age=0",
    "DNT":                       "1",
}
SESSION.headers.update(HEADERS)


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_soup(url: str, referer: str = None):
    try:
        headers = {}
        if referer:
            headers["Referer"] = referer
        time.sleep(1.5)   # be polite; also helps avoid 403 rate limits
        r = SESSION.get(url, timeout=20, headers=headers)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"  ⚠  fetch error {url}: {e}")
        return None


def make_id(*parts: str) -> str:
    return hashlib.md5("-".join(parts).encode()).hexdigest()[:12]


def is_upcoming(d: date) -> bool:
    return TODAY <= d <= TODAY + timedelta(days=CUTOFF_DAYS)


def fmt_date(d: date) -> str:
    return d.strftime("%-m/%-d/%Y")          # e.g. "6/12/2026"


def parse_month_year_from_url(url: str):
    """Extract month=M&year=YYYY from CivicPlus calendar URLs."""
    m = re.search(r"month=(\d+)&year=(\d{4})", url)
    return (int(m.group(1)), int(m.group(2))) if m else None


# ── Scraper: City of Plantation (Granicus CMS) ────────────────────────────────

def scrape_plantation() -> list[dict]:
    """
    Scrapes the Parks & Rec events calendar.
    Paginates through all upcoming pages.
    """
    base = "https://www.plantation.org/government/departments/parks-recreation/events"
    events = []
    page = 1

    while True:
        url = base if page == 1 else f"{base}/-npage-{page}"
        print(f"  plantation.org page {page}: {url}")
        ref = "https://www.plantation.org/government/departments/parks-recreation"
        soup = get_soup(url, referer=ref)
        if not soup:
            break

        # Event links are anchors pointing to /Home/Components/Calendar/Event/
        links = soup.find_all("a", href=re.compile(r"/Home/Components/Calendar/Event/"))
        if not links:
            break

        new_events = 0
        for a in links:
            href = a.get("href", "")
            event_url = urljoin("https://www.plantation.org", href)

            # Title is in an <h2> or <h3> inside the <a>
            title_el = a.find(re.compile(r"h[23]"))
            title = title_el.get_text(strip=True) if title_el else ""
            if not title:
                continue

            # Dates appear as MM/DD/YYYY in the link text
            text = a.get_text(" ")
            date_matches = re.findall(r"(\d{2}/\d{2}/\d{4})", text)
            time_matches = re.findall(r"(\d{1,2}:\d{2}\s*[AP]M)", text)

            if not date_matches:
                continue

            try:
                ev_date = datetime.strptime(date_matches[0], "%m/%d/%Y").date()
            except ValueError:
                continue

            if not is_upcoming(ev_date):
                continue

            time_str = ""
            if time_matches:
                time_str = time_matches[0]
                if len(time_matches) >= 2:
                    time_str += f" – {time_matches[1]}"

            events.append({
                "id":          make_id("plantation", title, str(ev_date)),
                "title":       title,
                "date":        str(ev_date),
                "date_fmt":    fmt_date(ev_date),
                "time":        time_str,
                "city":        "Plantation",
                "source_name": "City of Plantation",
                "source_url":  event_url,
            })
            new_events += 1

        # Check for next page link
        next_link = soup.find("a", string=re.compile(r"Next\s*»|Next\s+Page", re.I))
        if not next_link or new_events == 0 or page >= 10:
            break
        page += 1

    print(f"  → {len(events)} Plantation events")
    return events


# ── Scraper: City of Pembroke Pines (CivicPlus CMS) ──────────────────────────

def scrape_ppines() -> list[dict]:
    """
    Scrapes Pembroke Pines Special Events page.
    Grabs all Calendar.aspx?EID= links directly (both upcoming section and
    year table), parses date from link text + URL params.
    """
    url = "https://www.ppines.com/325/Special-Events"
    print(f"  ppines.com: {url}")
    soup = get_soup(url, referer="https://www.ppines.com/163/City-Departments")
    if not soup:
        return []

    events = []
    seen_ids = set()

    # Grab every calendar event link on the page
    for a in soup.find_all("a", href=re.compile(r"Calendar\.aspx.*EID=", re.I)):
        href = a.get("href", "")
        event_url = urljoin("https://www.ppines.com", href)
        my = parse_month_year_from_url(href)
        date_text = a.get_text(strip=True)   # e.g. "June 12"

        # Parse date: "June 12" + year from URL
        try:
            year = my[1] if my else TODAY.year
            ev_date = datetime.strptime(f"{date_text} {year}", "%B %d %Y").date()
            if ev_date < TODAY and (TODAY - ev_date).days > 14:
                ev_date = ev_date.replace(year=ev_date.year + 1)
        except ValueError:
            continue

        if not is_upcoming(ev_date):
            continue

        # Structure: <p><span><a>June 12</a></span>\xa0 | Mayor's Kids Day</p>
        # Walk up to the enclosing <p> and extract text after the pipe.
        p_el = a.find_parent("p")
        line_text = p_el.get_text(" ") if p_el else ""
        pipe_match = re.search(r"\|\s*(.+)", line_text)
        title = pipe_match.group(1).strip() if pipe_match else date_text

        if not title:
            continue

        eid_match = re.search(r"EID=(\d+)", href)
        ev_id = make_id("ppines", eid_match.group(1) if eid_match else title, str(ev_date))
        if ev_id in seen_ids:
            continue
        seen_ids.add(ev_id)

        events.append({
            "id":          ev_id,
            "title":       title,
            "date":        str(ev_date),
            "date_fmt":    fmt_date(ev_date),
            "time":        "",
            "city":        "Pembroke Pines",
            "source_name": "City of Pembroke Pines",
            "source_url":  event_url,
        })


    print(f"  → {len(events)} Pembroke Pines events")
    return events


# ── Scraper: City of Weston (Granicus CMS) ───────────────────────────────────

# Keywords that indicate a Parks/Recreation or community event vs. routine govt
WESTON_INCLUDE_KEYWORDS = re.compile(
    r"festival|concert|parade|event|celebration|fair|fun|movie|race|run|walk|"
    r"arts?|market|hunt|halloween|holiday|kids?|youth|family|camp|"
    r"chillin|bso|splash|brew|music|food|dance|fitness|yoga|hike|bike|"
    r"pines|weston|community|heritage|july 4|4th of july|independence",
    re.I
)
WESTON_EXCLUDE_KEYWORDS = re.compile(
    r"commission meeting|magistrate|hearing|board meeting|public meeting|"
    r"workshop \(staff\)|procurement|bid|election|budget",
    re.I
)


def scrape_weston() -> list[dict]:
    """
    Scrapes Weston's events calendar month by month (current + next 3 months).
    Filters to Parks & Recreation / community events.
    """
    base = "https://www.westonfl.org/about/events-calendar"
    events = []
    seen_ids = set()

    # Generate months to scrape: current + next 3
    months_to_scrape = []
    for delta in range(4):
        target = TODAY.replace(day=1) + timedelta(days=32 * delta)
        target = target.replace(day=1)
        months_to_scrape.append((target.month, target.year))

    for month, year in months_to_scrape:
        url = f"{base}/-curm-{month}/-cury-{year}"
        print(f"  westonfl.org {year}-{month:02d}: {url}")
        ref = "https://www.westonfl.org/about/events-calendar"
        soup = get_soup(url, referer=ref)
        if not soup:
            continue

        # Events appear as <a href="/Home/Components/Calendar/Event/{id}/...">
        for a in soup.find_all("a", href=re.compile(r"/Home/Components/Calendar/Event/")):
            href = a.get("href", "")
            event_url = urljoin("https://www.westonfl.org", href)
            title = a.get("title") or a.get_text(strip=True)
            if not title:
                continue

            # Skip government-only events
            if WESTON_EXCLUDE_KEYWORDS.search(title):
                continue
            # Only keep community/parks events
            if not WESTON_INCLUDE_KEYWORDS.search(title):
                continue

            # Date comes from the surrounding table cell context
            # Each <td> in the calendar grid contains: "day_number\n[time][title]..."
            td = a.find_parent("td")
            ev_date = None
            if td:
                # The day number is the first text node in the cell
                td_text = td.get_text(" ").strip()
                day_match = re.match(r"^(\d{1,2})\b", td_text)
                if day_match:
                    day = int(day_match.group(1))
                    try:
                        ev_date = date(year, month, day)
                    except ValueError:
                        pass

            if not ev_date or not is_upcoming(ev_date):
                continue

            # Extract time from text before the link (e.g. "5:30 PM[Chillin' with BSO]")
            prev_text = ""
            for sibling in a.previous_siblings:
                t = str(sibling).strip()
                if t:
                    prev_text = t
                    break
            time_match = re.search(r"(\d{1,2}:\d{2}\s*[AP]M)", prev_text)
            time_str = time_match.group(1) if time_match else ""

            ev_id = make_id("weston", title, str(ev_date))
            if ev_id in seen_ids:
                continue
            seen_ids.add(ev_id)

            events.append({
                "id":          ev_id,
                "title":       title,
                "date":        str(ev_date),
                "date_fmt":    fmt_date(ev_date),
                "time":        time_str,
                "city":        "Weston",
                "source_name": "City of Weston",
                "source_url":  event_url,
            })

    print(f"  → {len(events)} Weston events")
    return events


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print(f"\n🗓  LeaveWithDad Event Scraper — {TODAY.isoformat()}")
    print(f"   Output: {OUTPUT_FILE}\n")

    all_events: list[dict] = []

    print("Scraping Plantation...")
    all_events.extend(scrape_plantation())

    print("\nScraping Pembroke Pines...")
    all_events.extend(scrape_ppines())

    print("\nScraping Weston...")
    all_events.extend(scrape_weston())

    # Sort by date
    all_events.sort(key=lambda e: e["date"])

    # Deduplicate by id
    seen = set()
    deduped = []
    for ev in all_events:
        if ev["id"] not in seen:
            seen.add(ev["id"])
            deduped.append(ev)

    payload = {
        "scraped_at": datetime.utcnow().isoformat() + "Z",
        "event_count": len(deduped),
        "events": deduped,
    }

    OUTPUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\n✅ Wrote {len(deduped)} events to {OUTPUT_FILE}\n")

    # Summary by city
    from collections import Counter
    by_city = Counter(e["city"] for e in deduped)
    for city, count in sorted(by_city.items()):
        print(f"   {city:20s} {count} events")
    print()


if __name__ == "__main__":
    main()
