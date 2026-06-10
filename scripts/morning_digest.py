"""
leavewithdad.com — Morning Stats Digest
Runs in GitHub Actions. Fetches GA4, Search Console, AdSense data,
asks Claude for analysis, and emails dad@leavewithdad.com.
"""

import os
import json
import base64
import datetime
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import anthropic
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, OrderBy
)

# ── Config ────────────────────────────────────────────────────────────────────
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
    token_data  = os.environ["GOOGLE_TOKEN_JSON"]
    secret_data = os.environ["GOOGLE_CLIENT_SECRET_JSON"]

    # Write to temp files
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write(token_data)
        token_path = f.name

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    os.unlink(token_path)

    if creds.expired and creds.refresh_token:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(secret_data)
            secret_path = f.name
        creds.refresh(Request())
        os.unlink(secret_path)

    return creds

# ── Date helpers ──────────────────────────────────────────────────────────────
def yesterday():
    return (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

def sc_date():
    # Search Console lags ~3 days
    return (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")

def prev_week_range():
    end   = datetime.date.today() - datetime.timedelta(days=2)
    start = end - datetime.timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

# ── GA4 ───────────────────────────────────────────────────────────────────────
def get_ga4_stats(creds):
    client = BetaAnalyticsDataClient(credentials=creds)
    yest   = yesterday()
    pw_start, pw_end = prev_week_range()

    def run(start, end, dimensions=None, metrics=None, limit=10):
        dims    = [Dimension(name=d) for d in (dimensions or [])]
        mets    = [Metric(name=m) for m in (metrics or [])]
        req     = RunReportRequest(
            property=GA4_PROPERTY,
            date_ranges=[DateRange(start_date=start, end_date=end)],
            dimensions=dims,
            metrics=mets,
            limit=limit,
        )
        if dimensions:
            req.order_bys = [OrderBy(metric=OrderBy.MetricOrderBy(metric_name=metrics[0]), desc=True)]
        return client.run_report(req)

    # Yesterday overview
    ov = run(yest, yest, metrics=["sessions", "screenPageViews", "averageSessionDuration", "bounceRate"])
    if ov.rows:
        r = ov.rows[0].metric_values
        sessions  = int(r[0].value)
        pageviews = int(r[1].value)
        avg_dur   = round(float(r[2].value))
        bounce    = round(float(r[3].value) * 100, 1)
    else:
        sessions = pageviews = avg_dur = bounce = 0

    # Top 5 pages yesterday
    pages_r = run(yest, yest, dimensions=["pagePath"], metrics=["screenPageViews"], limit=5)
    top_pages = [(row.dimension_values[0].value, int(row.metric_values[0].value)) for row in pages_r.rows]

    # Previous week overview for comparison
    pw_ov = run(pw_start, pw_end, metrics=["sessions", "screenPageViews"])
    if pw_ov.rows:
        pw_r          = pw_ov.rows[0].metric_values
        pw_sessions   = round(int(pw_r[0].value) / 7)
        pw_pageviews  = round(int(pw_r[1].value) / 7)
    else:
        pw_sessions = pw_pageviews = 0

    return {
        "sessions": sessions, "pageviews": pageviews,
        "avg_duration": avg_dur, "bounce_rate": bounce,
        "top_pages": top_pages,
        "prev_week_avg_sessions": pw_sessions,
        "prev_week_avg_pageviews": pw_pageviews,
    }

# ── Search Console ────────────────────────────────────────────────────────────
def get_sc_stats(creds):
    service = build("searchconsole", "v1", credentials=creds)
    date    = sc_date()
    try:
        result = service.searchanalytics().query(
            siteUrl=SC_SITE,
            body={"startDate": date, "endDate": date, "dimensions": []}
        ).execute()
        row = result.get("rows", [{}])[0]
        # Top queries
        q_result = service.searchanalytics().query(
            siteUrl=SC_SITE,
            body={"startDate": date, "endDate": date, "dimensions": ["query"], "rowLimit": 5}
        ).execute()
        top_queries = [
            (r["keys"][0], int(r.get("clicks", 0)), round(r.get("position", 0), 1))
            for r in q_result.get("rows", [])
        ]
        return {
            "clicks": int(row.get("clicks", 0)),
            "impressions": int(row.get("impressions", 0)),
            "ctr": round(row.get("ctr", 0) * 100, 2),
            "position": round(row.get("position", 0), 1),
            "top_queries": top_queries,
            "date": date,
        }
    except Exception as e:
        return {"clicks": 0, "impressions": 0, "ctr": 0.0, "position": 0.0, "top_queries": [], "date": date, "error": str(e)}

# ── AdSense ───────────────────────────────────────────────────────────────────
def get_adsense_stats(creds):
    service = build("adsense", "v2", credentials=creds)
    yest    = yesterday()
    y, m, d = int(yest[:4]), int(yest[5:7]), int(yest[8:10])
    try:
        result = service.accounts().reports().generate(
            account=f"accounts/{ADSENSE_PUB}",
            dateRange="CUSTOM",
            startDate_year=y, startDate_month=m, startDate_day=d,
            endDate_year=y,   endDate_month=m,   endDate_day=d,
            metrics=["ESTIMATED_EARNINGS", "IMPRESSIONS", "PAGE_VIEWS_RPM", "CLICKS"],
        ).execute()
        rows = result.get("rows", [])
        if rows:
            c = rows[0].get("cells", [])
            return {
                "earnings":    round(float(c[0].get("value", 0)), 2),
                "impressions": int(c[1].get("value", 0)),
                "rpm":         round(float(c[2].get("value", 0)), 2),
                "ad_clicks":   int(c[3].get("value", 0)),
            }
    except Exception as e:
        return {"earnings": 0.0, "impressions": 0, "rpm": 0.0, "ad_clicks": 0, "error": str(e)}
    return {"earnings": 0.0, "impressions": 0, "rpm": 0.0, "ad_clicks": 0}

# ── Claude Analysis ───────────────────────────────────────────────────────────
def get_analysis(ga4, sc, adsense):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    sessions_delta = ""
    if ga4["prev_week_avg_sessions"] > 0:
        delta = round((ga4["sessions"] - ga4["prev_week_avg_sessions"]) / ga4["prev_week_avg_sessions"] * 100)
        sessions_delta = f" ({'+' if delta >= 0 else ''}{delta}% vs last week avg)"

    data_summary = f"""
leavewithdad.com — Yesterday's Stats

TRAFFIC (GA4):
- Sessions: {ga4['sessions']}{sessions_delta}
- Pageviews: {ga4['pageviews']}
- Avg session duration: {ga4['avg_duration']}s
- Bounce rate: {ga4['bounce_rate']}%
- Top pages: {', '.join([f"{p} ({v} views)" for p, v in ga4['top_pages'][:3]])}

SEARCH (Search Console — data from {sc['date']}):
- Clicks: {sc['clicks']}
- Impressions: {sc['impressions']}
- CTR: {sc['ctr']}%
- Avg position: {sc['position']}
- Top queries: {', '.join([f"{q} ({c} clicks, pos {p})" for q, c, p in sc['top_queries'][:3]])}

REVENUE (AdSense):
- Estimated earnings: ${adsense['earnings']}
- Impressions: {adsense['impressions']}
- RPM: ${adsense['rpm']}
- Ad clicks: {adsense['ad_clicks']}
"""

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": f"""You are analyzing daily website stats for leavewithdad.com, a content site about activities and practical tips for dads. The site makes money from ads.

Here are yesterday's stats:
{data_summary}

Write a SHORT morning digest (max 150 words) that:
1. Highlights 1-2 notable things (good or bad)
2. Gives 2-3 specific, actionable recommendations to improve traffic or revenue
3. Flags anything that needs attention

Be direct and specific. No fluff. Format as plain paragraphs, no bullet points."""
        }]
    )
    return message.content[0].text

# ── Email ─────────────────────────────────────────────────────────────────────
def build_email(ga4, sc, adsense, analysis):
    date_label = datetime.date.today().strftime("%B %d, %Y")
    yest       = yesterday()

    sessions_delta_html = ""
    if ga4["prev_week_avg_sessions"] > 0:
        delta = round((ga4["sessions"] - ga4["prev_week_avg_sessions"]) / ga4["prev_week_avg_sessions"] * 100)
        color = "#2a9d5c" if delta >= 0 else "#e63946"
        sessions_delta_html = f" <span style='color:{color};font-size:12px'>({'+' if delta >= 0 else ''}{delta}% vs last week)</span>"

    top_pages_rows = "".join([
        f"<tr{'style=background:#f9f9f9' if i % 2 else ''}>"
        f"<td style='padding:4px 8px;color:#444;font-size:13px'>{p}</td>"
        f"<td style='padding:4px 8px;text-align:right;font-size:13px'>{v:,}</td></tr>"
        for i, (p, v) in enumerate(ga4["top_pages"])
    ])

    top_queries_rows = "".join([
        f"<tr{'style=background:#f9f9f9' if i % 2 else ''}>"
        f"<td style='padding:4px 8px;color:#444;font-size:13px'>{q}</td>"
        f"<td style='padding:4px 8px;text-align:right;font-size:13px'>{c}</td>"
        f"<td style='padding:4px 8px;text-align:right;font-size:13px'>#{p}</td></tr>"
        for i, (q, c, p) in enumerate(sc["top_queries"])
    ]) if sc["top_queries"] else "<tr><td colspan='3' style='padding:8px;color:#aaa;font-size:13px'>No query data yet</td></tr>"

    analysis_html = analysis.replace("\n\n", "</p><p>").replace("\n", " ")

    html = f"""
    <html><body style="font-family:Arial,sans-serif;max-width:620px;margin:auto;color:#222;padding:16px">
      <h2 style="border-bottom:3px solid #e63946;padding-bottom:8px;margin-bottom:20px">
        ☀️ leavewithdad.com &nbsp;·&nbsp; {date_label}
      </h2>

      <!-- Claude Analysis -->
      <div style="background:#fef9f0;border-left:4px solid #e63946;padding:12px 16px;margin-bottom:24px;border-radius:4px">
        <p style="margin:0 0 4px 0;font-size:11px;color:#aaa;text-transform:uppercase;letter-spacing:1px">Today's Analysis</p>
        <p style="margin:0;font-size:14px;line-height:1.6">{analysis_html}</p>
      </div>

      <!-- GA4 -->
      <h3 style="color:#e63946;margin-bottom:8px">📊 Traffic — yesterday ({yest})</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
        <tr><td style="padding:5px 8px;color:#555">Sessions</td>
            <td style="padding:5px 8px;text-align:right"><b>{ga4['sessions']:,}</b>{sessions_delta_html}</td></tr>
        <tr style="background:#f9f9f9"><td style="padding:5px 8px;color:#555">Pageviews</td>
            <td style="padding:5px 8px;text-align:right"><b>{ga4['pageviews']:,}</b></td></tr>
        <tr><td style="padding:5px 8px;color:#555">Avg. Session Duration</td>
            <td style="padding:5px 8px;text-align:right"><b>{ga4['avg_duration']}s</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:5px 8px;color:#555">Bounce Rate</td>
            <td style="padding:5px 8px;text-align:right"><b>{ga4['bounce_rate']}%</b></td></tr>
      </table>
      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
        <tr style="background:#f0f0f0">
          <th style="padding:5px 8px;text-align:left;font-weight:600">Top Pages</th>
          <th style="padding:5px 8px;text-align:right;font-weight:600">Views</th>
        </tr>
        {top_pages_rows}
      </table>

      <!-- Search Console -->
      <h3 style="color:#e63946;margin-bottom:8px">🔍 Search — data from {sc['date']}</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:8px">
        <tr><td style="padding:5px 8px;color:#555">Clicks</td>
            <td style="padding:5px 8px;text-align:right"><b>{sc['clicks']:,}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:5px 8px;color:#555">Impressions</td>
            <td style="padding:5px 8px;text-align:right"><b>{sc['impressions']:,}</b></td></tr>
        <tr><td style="padding:5px 8px;color:#555">CTR</td>
            <td style="padding:5px 8px;text-align:right"><b>{sc['ctr']}%</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:5px 8px;color:#555">Avg. Position</td>
            <td style="padding:5px 8px;text-align:right"><b>{sc['position']}</b></td></tr>
      </table>
      <table style="width:100%;border-collapse:collapse;font-size:13px;margin-bottom:20px">
        <tr style="background:#f0f0f0">
          <th style="padding:5px 8px;text-align:left;font-weight:600">Top Queries</th>
          <th style="padding:5px 8px;text-align:right;font-weight:600">Clicks</th>
          <th style="padding:5px 8px;text-align:right;font-weight:600">Position</th>
        </tr>
        {top_queries_rows}
      </table>

      <!-- AdSense -->
      <h3 style="color:#e63946;margin-bottom:8px">💰 AdSense — yesterday ({yest})</h3>
      <table style="width:100%;border-collapse:collapse;margin-bottom:24px">
        <tr><td style="padding:5px 8px;color:#555">Estimated Earnings</td>
            <td style="padding:5px 8px;text-align:right"><b>${adsense['earnings']:.2f}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:5px 8px;color:#555">Impressions</td>
            <td style="padding:5px 8px;text-align:right"><b>{adsense['impressions']:,}</b></td></tr>
        <tr><td style="padding:5px 8px;color:#555">RPM</td>
            <td style="padding:5px 8px;text-align:right"><b>${adsense['rpm']:.2f}</b></td></tr>
        <tr style="background:#f9f9f9"><td style="padding:5px 8px;color:#555">Ad Clicks</td>
            <td style="padding:5px 8px;text-align:right"><b>{adsense['ad_clicks']:,}</b></td></tr>
      </table>

      <p style="color:#bbb;font-size:11px;border-top:1px solid #eee;padding-top:12px;margin-top:8px">
        leavewithdad.com · automated morning digest · github actions
      </p>
    </body></html>
    """
    return html

def send_email(creds, html):
    service   = build("gmail", "v1", credentials=creds)
    msg       = MIMEMultipart("alternative")
    msg["Subject"] = f"☀️ leavewithdad stats — {datetime.date.today().strftime('%b %d')}"
    msg["From"]    = "diegomgalvaoc@gmail.com"
    msg["To"]      = RECIPIENT
    msg.attach(MIMEText(html, "html"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId="me", body={"raw": raw}).execute()
    print(f"Email sent to {RECIPIENT}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("Authenticating...")
    creds = get_credentials()

    print("Fetching GA4...")
    ga4 = get_ga4_stats(creds)

    print("Fetching Search Console...")
    sc = get_sc_stats(creds)

    print("Fetching AdSense...")
    adsense = get_adsense_stats(creds)

    print("Generating Claude analysis...")
    analysis = get_analysis(ga4, sc, adsense)
    print(f"Analysis preview: {analysis[:100]}...")

    print("Building and sending email...")
    html = build_email(ga4, sc, adsense, analysis)
    send_email(creds, html)
    print("Done.")

if __name__ == "__main__":
    main()
