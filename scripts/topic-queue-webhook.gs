/**
 * leavewithdad — Topic Queue Webhook
 * Deployed as a Google Apps Script Web App.
 *
 * Accepts POST requests with JSON body:
 *   { "slug": "non-emergency-police-plantation", "status": "draft" }
 *   { "slug": "non-emergency-police-plantation", "status": "published", "date": "2026-06-11" }
 *
 * Also accepts GET requests with query params:
 *   ?slug=non-emergency-police-plantation&status=draft
 *   ?slug=non-emergency-police-plantation&status=published&date=2026-06-11
 *
 * Finds the row where column C (Slug) matches, then updates:
 *   - Column E (Status)
 *   - Column G (Published Date) — only when status = "published" and date is provided
 *
 * When status = "draft", sends an email notification to NOTIFY_EMAIL.
 *
 * Returns JSON: { "ok": true, "row": 4, "slug": "...", "status": "..." }
 *             or { "ok": false, "error": "..." }
 */

var SHEET_ID    = "1Yftu5cFEd0BP90Ea4LiDEkSN2GUAS56mIlYbH5lMDo4";
var SHEET_NAME  = "Sheet1";
var NOTIFY_EMAIL = "diegomgalvaoc@gmail.com";
var SITE_URL    = "https://leavewithdad.com";

var COL_SLUG      = 3; // C
var COL_TITLE     = 2; // B
var COL_STATUS    = 5; // E
var COL_PUBLISHED = 7; // G

function doGet(e) {
  try {
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
      // Send email notification
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
      subject = "📝 Draft ready: " + title;
      body    = "Draft ready for review.\n\n"
              + "Article: " + title + "\n"
              + "Slug:    " + slug + "\n"
              + "Review:  " + SITE_URL + "/drafts/" + slug + "/\n\n"
              + "Open Cowork and say \"publish " + slug + "\" to go live, or reply with edits.";
    } else if (status === "published") {
      subject = "✅ Published: " + title;
      body    = "Article published.\n\n"
              + "Article: " + title + "\n"
              + "URL:     " + SITE_URL + "/" + slug + "/\n"
              + "Date:    " + (date || "today");
    } else {
      return; // no notification for other statuses
    }
    GmailApp.sendEmail(NOTIFY_EMAIL, subject, body);
  } catch (err) {
    // email failure is non-fatal — sheet update already happened
    Logger.log("Email send failed: " + err.toString());
  }
}

function respond(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Optional: test locally inside Apps Script editor
function _test() {
  var fakePost = {
    postData: {
      contents: JSON.stringify({ slug: "diy-slab", status: "draft" })
    }
  };
  Logger.log(doPost(fakePost).getContent());
}
