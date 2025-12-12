/**
 * Always-free pipeline:
 * Google Form -> Google Sheet -> Apps Script trigger -> GitHub repository_dispatch -> GitHub Actions -> email
 */

const GITHUB_OWNER = "YOUR_GH_USERNAME_OR_ORG";
const GITHUB_REPO  = "redentnova-customer-complaint-mail";
const DISPATCH_TYPE = "form_submit";

/**
 * Store your PAT in Script Properties:
 *  - Project Settings -> Script Properties -> add key: GITHUB_PAT
 */
function getPat_() {
  const pat = PropertiesService.getScriptProperties().getProperty("GITHUB_PAT");
  if (!pat) throw new Error("Missing Script Property GITHUB_PAT");
  return pat;
}

function onFormSubmit(e) {
  const namedValues = (e && e.namedValues) ? e.namedValues : null;

  const fields = {};
  if (namedValues) {
    Object.keys(namedValues).forEach((k) => {
      const v = namedValues[k];
      fields[k] = Array.isArray(v) ? (v.length === 1 ? v[0] : v.join(", ")) : v;
    });
  } else {
    fields["Timestamp"] = new Date().toISOString();
  }

  // GDPR-friendly: do NOT auto-collect customer email addresses.
  // If your Form previously had an email field, remove it from the payload.
  delete fields["Email Address"];
  delete fields["Email"]; // common variations

  const ts = String(fields["Timestamp"] || new Date().toISOString());
  const row = (e && e.range) ? e.range.getRow() : 0;
  const submissionId = `${ts}#row${row}`;

  // Fixed internal recipient(s)
  const recipients = ["lab@redentnova.de"];

  const payload = {
    event_type: DISPATCH_TYPE,
    client_payload: {
      submission_id: submissionId,
      form_title: "ReDent Nova — Customer Complaint",
      timestamp: ts,
      fields: fields,
      email_to: recipients
    }
  };

  const url = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/dispatches`;

  const res = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    headers: {
      Authorization: "Bearer " + getPat_(),
      Accept: "application/vnd.github+json"
    },
    muteHttpExceptions: true
  });

  const code = res.getResponseCode();
  if (code >= 300) {
    throw new Error("GitHub dispatch failed: " + code + " " + res.getContentText());
  }
}
