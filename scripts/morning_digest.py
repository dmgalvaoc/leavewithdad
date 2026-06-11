"""
leavewithdad.com — Morning Stats Digest
Fetches yesterday's data from GA4, Search Console, and AdSense,
then emails a digest to dad@leavewithdad.com via Gmail API.

Credentials: reads GOOGLE_TOKEN_JSON env var (GitHub Actions secret),
falls back to token.json in the script directory for local runs.
"""

import os
import json
import base64
import datetime
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy
)

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE   = os.path.join(SCRIPT_DIR, "..", "token.json")  # local fallback
GA4_PROPERTY = "properties/540949581"
SC_SITE      = "https://leavewithdad.com/"
ADSENSE_PUB  = "pub-8668596875719653"
RECIPIENT    = "dad@leavewithdad.com"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/adsense.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]

# ── Auth ──────────────────────────────────────────────────────────────────────
def get_credentials():
    token_json = os.environ.get("GOOGLE_TOKEN_JSON")
    if token_json:
        # GitHub Actions: write env var to a temp file
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(token_json)
        tmp.close()
        token_path = tmp.name
    else:
        # Local run: use token.json next to the project root
        token_path = TOKEN_FILE

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds

# ── Date helpers ──────────────────────────────────────────────────────────────
def yesterday():
    return (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

def sc_date():
    # Search Console data lags ~2-3 days
    return (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")

# ── GA4 ───────────────────────────────────────────────────────────────────────
def get_ga4_stats(creds):
    client = BetaAnalyticsDataClient(credentials=creds)
    yest = yesterday()

    overview = client.run_report(RunReportRequest(
        property=GA4_PROPERTY,
        date_ranges=[DateRange(start_date=yest, end_date=yest)],
        metrics=[Metric(name="sessions"), Metric(name="screenPageViews")],
    ))
    sessions  = int(overview.rows[0].metric_values[0].value) if overview.rows else 0
    pageviews = int(overview.rows[0].metric_values[1].value) if overview.rows else 0

    pages_report = client.run_report(RunReportRequest(
        property=GA4_PROPERTY,
        date_ranges=[DateRange(start_date=yest, end_date=yest)],
        dimensions=[Dimension(name="pagePath")],
        metrics=[Metric(name="screenPageViews")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=5,
    ))
    top_pages = [
        (row.dimension_values[0].value, int(row.metric_values[0].value))
        for row in pages_report.rows
    ]

    return {"sessions": sessions, "pageviews": pageviews, "top_pages": top_pages}

# ── Search Console ────────────────────────────────────────────────────────────
def get_search_console_stats(creds):
    service = build("searchconsole", "v1", credentials=creds)
    date = sc_date()

    try:
        result = service.searchanalytics().query(
            siteUrl=SC_SITE,
            body={"startDate": date, "endDate": date, "dimensions": []},
        ).execute()
        row = result.get("rows", [{}])[0]
        return {
            "clicks":      int(row.get("clicks", 0)),
            "impressions": int(row.get("impressions", 0)),
            "ctr":         round(row.get("ctr", 0) * 100, 2),
            "position":    round(row.get("position", 0), 1),
            "date":        date,
        }
    except Exception as e:
        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0, "date": date, "error": str(e)}

# ── AdSense ───────────────────────────────────────────────────────────────────
def get_adsense_stats(creds):
    service = build("adsense", "v2", credentials=creds)
    yest = yesterday()

    try:
        result = service.accounts().reports().generate(
            account=f"accounts/{ADSENSE_PUB}",
            dateRange="CUSTOM",
            startDate_year=int(yest[:4]),
            startDate_month=int(yest[5:7]),
            startDate_day=int(yest[8:10]),
            endDate_year=int(yest[:4]),
            endDate_month=int(yest[5:7]),
            endDate_day=int(yest[8:10]),
            metrics=["ESTIMATED_EARNINGS", "IMPRESSIONS", "PAGE_VIEWS_RPM", "CLICKS"],
        ).execute()
        rows = result.get("rows", [])
        if rows:
            cells = rows[0].get("cells", [])
            return {
                "earnings":    float(cells[0].get("value", 0)),
                "impressions": int(cells[1].get("value", 0)),
                "rpm":         float(cells[2].get("value", 0)),
                "ad_clicks":   int(cells[3].get("value", 0)),
            }
    except Exception as e:
        return {"earnings": 0.0, "impressions": 0, "rpm": 0.0, "ad_clicks": 0, "error": str(e)}

    return {"earnings": 0.0, "impressions": 0, "rpm": 0.0, "ad_clicks": 0}

# ── Email ─────────────────────────────────────────────────────────────────────
def build_email(ga4, sc, adsense):
    date_label = datetime.date.today().strftime("%B %d, %Y")

    top_pages_rows = "".join([
        f"<tr><td style='padding:4px 8px;color:#444'>{p}</td>"
        f"<td style='padding:4px 8px;text-align:right;color:#222'>{v:,}</td></tr>"
        for p, v in ga4["top_pages"]
    ])

    sc_note = f"(data from {sc['date']} — SC lags ~2-3 days)"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:auto;color:#222">
      <h2 style="border-bottom:2px solid #e63946;padding-bottom:8px">
        🌅 leavewithdad.com — {date_label}
      </h2>

      <h3 style="color:#e63946">📊 Traffic (GA4 — yesterday)</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:4px 8px;color:#444">Sessions</td>
            <td style="padding:4px 8px;text-align:right"><b>{ga4['sessions']:,}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:4px 8px;color:#444">Pageviews</td>
            <td style="padding:4px 8px;text-align:right"><b>{ga4['pageviews']:,}</b></td></tr>
      </table>

      <h4 style="color:#555;margin-top:16px">Top Pages</h4>
      <table style="width:100%;border-collapse:collapse;font-size:13px">
        <tr style="background:#f0f0f0"><th style="padding:4px 8px;text-align:left">Page</th>
            <th style="padding:4px 8px;text-align:right">Views</th></tr>
        {top_pages_rows}
      </table>

      <h3 style="color:#e63946;margin-top:24px">🔍 Search Console {sc_note}</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:4px 8px;color:#444">Clicks</td>
            <td style="padding:4px 8px;text-align:right"><b>{sc['clicks']:,}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:4px 8px;color:#444">Impressions</td>
            <td style="padding:4px 8px;text-align:right"><b>{sc['impressions']:,}</b></td></tr>
        <tr><td style="padding:4px 8px;color:#444">CTR</td>
            <td style="padding:4px 8px;text-align:right"><b>{sc['ctr']}%</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:4px 8px;color:#444">Avg. Position</td>
            <td style="padding:4px 8px;text-align:right"><b>{sc['position']}</b></td></tr>
      </table>

      <h3 style="color:#e63946;margin-top:24px">💰 AdSense (yesterday)</h3>
      <table style="width:100%;border-collapse:collapse">
        <tr><td style="padding:4px 8px;color:#444">Estimated Earnings</td>
            <td style="padding:4px 8px;text-align:right"><b>${adsense['earnings']:.2f}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:4px 8px;color:#444">Impressions</td>
            <td style="padding:4px 8px;text-align:right"><b>{adsense['impressions']:,}</b></td></tr>
        <tr><td style="padding:4px 8px;color:#444">RPM</td>
            <td style="padding:4px 8px;text-align:right"><b>${adsense['rpm']:.2f}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:4px 8px;color:#444">Ad Clicks</td>
            <td style="padding:4px 8px;text-align:right"><b>{adsense['ad_clicks']:,}</b></td></tr>
      </table>

      <p style="color:#aaa;font-size:11px;margin-top:32px;border-top:1px solid #eee;padding-top:8px">
        leavewithdad.com · automated morning digest
      </p>
    </body></html>
    """
    return html

def send_email(creds, html):
    service = build("gmail", "v1", credentials=creds)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ leavewithdad stats — {datetime.date.today().strftime('%b %d')}"
    msg["From"]    = RECIPIENT
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print("Email sent.")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Fetching stats...")
    creds   = get_credentials()
    ga4     = get_ga4_stats(creds)
    sc      = get_search_console_stats(creds)
    adsense = get_adsense_stats(creds)

    print(f"GA4     — sessions: {ga4['sessions']}, pageviews: {ga4['pageviews']}")
    print(f"SC      — clicks: {sc['clicks']}, impressions: {sc['impressions']}")
    print(f"AdSense — earnings: ${adsense['earnings']:.2f}, RPM: ${adsense['rpm']:.2f}")

    html = build_email(ga4, sc, adsense)
    send_email(creds, html)

if __name__ == "__main__":
    main()
