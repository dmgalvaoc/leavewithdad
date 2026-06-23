/**
 * leavewithdad — Topic Queue Webhook
 * Deployed as a Google Apps Script Web App.
 *
 * GET ?action=next
 *   Returns the idea row scheduled for today as JSON:
 *   { "ok": true, "title": "...", "slug": "...", "category": "...",
 *     "notes": "...", "affiliateLinks": ["url1", "url2"] }
 *   Returns { "ok": false, "error": "No idea scheduled for today (YYYY-MM-DD)" } if none match.
 *
 * GET ?slug=...&status=draft|published[&date=YYYY-MM-DD]
 *   Updates the sheet row matching slug.
 *
 * POST { "slug": "...", "status": "draft"|"published", "date": "..." }
 *   Same as GET update but via POST body.
 *
 * Returns JSON: { "ok": true, ... } or { "ok": false, "error": "..." }
 */

var SHEET_ID         = "1Yftu5cFEd0BP90Ea4LiDEkSN2GUAS56mIlYbH5lMDo4";
var SHEET_NAME       = "Sheet1";
var NOTIFY_EMAIL     = "dad@leavewithdad.com";
var SITE_URL         = "https://leavewithdad.com";
var ASSETS_FOLDER_ID = "1IAQ-9A4hpxgMk3C8hd_aD8gn5nlB0ukc";

var COL_TITLE     = 2;  // B
var COL_SLUG      = 3;  // C
var COL_CATEGORY  = 4;  // D
var COL_STATUS    = 5;  // E
var COL_SCHED     = 6;  // F
var COL_PUBLISHED = 7;  // G
var COL_NOTES     = 8;  // H
var COL_AFF1      = 9;  // I
var COL_AFF2      = 10; // J
var COL_AFF3      = 11; // K
var COL_AFF4      = 12; // L
var COL_PIMG1     = 13; // M — Product Image 1
var COL_PIMG2     = 14; // N — Product Image 2
var COL_PIMG3     = 15; // O — Product Image 3
var COL_PIMG4     = 16; // P — Product Image 4
var COL_POSTIMG1  = 17; // Q — Post Image 1
var COL_POSTIMG2  = 18; // R — Post Image 2
var COL_POSTIMG3  = 19; // S — Post Image 3

function doGet(e) {
  try {
    var action = (e.parameter.action || "").trim();
    if (action === "next") return getNextIdea();
    var slug   = (e.parameter.slug   || "").trim();
    var status = (e.parameter.status || "").trim();
    var date   = (e.parameter.date   || "").trim();
    return processUpdate(slug, status, date);
  } catch (err) {
    return respond({ ok: false, error: err.toString() });
  }
}

function doPost(e) {
  try {
    var body   = JSON.parse(e.postData.contents);
    var slug   = (body.slug   || "").trim();
    var status = (body.status || "").trim();
    var date   = (body.date   || "").trim();
    return processUpdate(slug, status, date);
  } catch (err) {
    return respond({ ok: false, error: err.toString() });
  }
}

function getNextIdea() {
  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.getSheets()[0];
  var data  = sheet.getDataRange().getValues();
  var tz    = Session.getScriptTimeZone();
  var today = Utilities.formatDate(new Date(), tz, "yyyy-MM-dd");

  for (var i = 1; i < data.length; i++) {
    var status = (data[i][COL_STATUS - 1] || "").trim().toLowerCase();
    if (status !== "idea") continue;

    var schedRaw  = data[i][COL_SCHED - 1];
    var schedDate = schedRaw ? Utilities.formatDate(new Date(schedRaw), tz, "yyyy-MM-dd") : "";
    if (schedDate !== today) continue;

    var affLinks = [
      (data[i][COL_AFF1 - 1] || "").trim(),
      (data[i][COL_AFF2 - 1] || "").trim(),
      (data[i][COL_AFF3 - 1] || "").trim(),
      (data[i][COL_AFF4 - 1] || "").trim()
    ].filter(function(l) { return l !== ""; });

    var productImages = [
      (data[i][COL_PIMG1 - 1] || "").trim(),
      (data[i][COL_PIMG2 - 1] || "").trim(),
      (data[i][COL_PIMG3 - 1] || "").trim(),
      (data[i][COL_PIMG4 - 1] || "").trim()
    ].filter(function(l) { return l !== ""; });

    var postImages = [
      (data[i][COL_POSTIMG1 - 1] || "").trim(),
      (data[i][COL_POSTIMG2 - 1] || "").trim(),
      (data[i][COL_POSTIMG3 - 1] || "").trim()
    ].filter(function(l) { return l !== ""; });

    return respond({
      ok:            true,
      row:           i + 1,
      title:         (data[i][COL_TITLE    - 1] || "").trim(),
      slug:          (data[i][COL_SLUG     - 1] || "").trim(),
      category:      (data[i][COL_CATEGORY - 1] || "").trim(),
      notes:         (data[i][COL_NOTES    - 1] || "").trim(),
      affiliateLinks: affLinks,
      productImages:  productImages,
      postImages:     postImages
    });
  }

  return respond({ ok: false, error: "No idea scheduled for today (" + today + ")" });
}

function processUpdate(slug, status, date) {
  if (!slug || !status) {
    return respond({ ok: false, error: "Missing slug or status" });
  }

  var ss    = SpreadsheetApp.openById(SHEET_ID);
  var sheet = ss.getSheetByName(SHEET_NAME) || ss.getSheets()[0];
  var data  = sheet.getDataRange().getValues();

  for (var i = 1; i < data.length; i++) {
    var rowSlug = (data[i][COL_SLUG - 1] || "").trim();
    if (rowSlug === slug) {
      var title = (data[i][COL_TITLE - 1] || slug).trim();
      sheet.getRange(i + 1, COL_STATUS).setValue(status);
      if (status === "published" && date) {
        sheet.getRange(i + 1, COL_PUBLISHED).setValue(date);
      }
      sendNotification(slug, title, status, date);
      return respond({ ok: true, row: i + 1, slug: slug, status: status });
    }
  }

  return respond({ ok: false, error: "Slug not found: " + slug });
}

function sendNotification(slug, title, status, date) {
  try {
    var subject, body;
    if (status === "draft") {
      subject = "Draft ready: " + title;
      body    = "Draft ready for review.\n\n"
              + "Article: " + title + "\n"
              + "Slug:    " + slug + "\n"
              + "Review:  " + SITE_URL + "/articles/" + slug + "/\n\n"
              + "Open Claude and say \"publish " + slug + "\" to go live, or reply with edits.";
    } else if (status === "published") {
      subject = "✅ Published: " + title;
      body    = "Article published.\n\n"
              + "Article: " + title + "\n"
              + "URL:     " + SITE_URL + "/" + slug + "/\n"
              + "Date:    " + (date || "today");
    } else {
      return;
    }
    GmailApp.sendEmail(NOTIFY_EMAIL, subject, body);
  } catch (err) {
    Logger.log("Email send failed: " + err.toString());
  }
}

function respond(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * checkDraftSignals — called by a daily time-driven trigger (7 am).
 * Scans Assets Drive folder for {slug}.draft signal files, updates sheet, deletes file.
 */
function checkDraftSignals() {
  var folder = DriveApp.getFolderById(ASSETS_FOLDER_ID);
  var files  = folder.getFiles();
  while (files.hasNext()) {
    var file = files.next();
    var name = file.getName();
    if (!name.endsWith(".draft")) continue;
    var slug = name.replace(/\.draft$/, "");
    try {
      processUpdate(slug, "draft", "");
      file.setTrashed(true);
      Logger.log("Processed draft signal: " + slug);
    } catch (err) {
      Logger.log("Error processing signal " + slug + ": " + err.toString());
    }
  }
}

function _test() {
  var fakePost = {
    postData: {
      contents: JSON.stringify({ slug: "diy-slab", status: "draft" })
    }
  };
  Logger.log(doPost(fakePost).getContent());
}
