const INTERNAL_RECIPIENT = "lab@redentnova.de";

// Keywords we treat as personal contact data when consent = NO
const PII_KEYWORDS = ["phone", "email"];

function onFormSubmit(e) {
  const form = FormApp.getActiveForm();
  const response = e.response;

  // ----- Build structured sections from the form submission -----
  const sections = buildSections_(form, response);

  // ----- Generate complaint metadata -----
  const complaintId = buildComplaintId_();
  const submissionTimestamp = new Date().toISOString();

  // ----- Consent (find by question title contains; later we can pin to itemId) -----
  const consent = extractConsent_(sections);
  const contactConsent = (consent === "yes") ? "yes" : "no";

  // ----- Apply masking if NO consent -----
  if (contactConsent !== "yes") {
    maskSections_(sections, PII_KEYWORDS);
  }

  // ----- Determine customer email if consent YES -----
  const customerEmail = (contactConsent === "yes") ? extractEmail_(sections) : "";

  // Always send to lab, customer only if consent yes + email exists
  const emailTo = [INTERNAL_RECIPIENT];
  if (customerEmail) emailTo.push(customerEmail);

  // ----- Write initial status row into your RESPONSE SHEET's spreadsheet -----
  // (We still use the linked response spreadsheet for status storage)
  writeInitialStatus_(complaintId);

  // ----- Dispatch to GitHub -----
  dispatchToGithub_({
    submission_id: complaintId,
    complaint_id: complaintId,
    submission_timestamp: submissionTimestamp,
    email_to: emailTo,
    contact_consent: contactConsent,
    sections: sections
  });
}


// ============================
// Build sections + rows
// ============================

function buildSections_(form, response) {
  // Build map: itemId -> { title, sectionTitle }
  const items = form.getItems();
  const itemMeta = {};
  let currentSectionTitle = "Form Details";

  for (const it of items) {
    const t = (it.getTitle() || "").trim();

    // Page break items act as "section headers"
    if (it.getType() === FormApp.ItemType.PAGE_BREAK) {
      currentSectionTitle = t || "Form Details";
      continue;
    }
    itemMeta[String(it.getId())] = {
      title: t || "Untitled Question",
      section: currentSectionTitle
    };
  }

  // Convert response itemResponses into ordered rows grouped by section
  const sectionOrder = [];
  const sectionMap = {}; // sectionTitle -> rows[]

  const itemResponses = response.getItemResponses();
  for (const ir of itemResponses) {
    const item = ir.getItem();
    const id = String(item.getId());

    const meta = itemMeta[id] || { title: item.getTitle() || "Untitled Question", section: "Form Details" };
    const sectionTitle = meta.section || "Form Details";
    const label = meta.title || "Untitled Question";

    let ans = ir.getResponse();
    let value = "";

    if (Array.isArray(ans)) value = ans.join(", ");
    else if (ans === null || ans === undefined) value = "";
    else value = String(ans);

    if (!sectionMap[sectionTitle]) {
      sectionMap[sectionTitle] = [];
      sectionOrder.push(sectionTitle);
    }
    sectionMap[sectionTitle].push({ label: label, value: value });
  }

  // Return ordered sections
  return sectionOrder.map(title => ({ title, rows: sectionMap[title] }));
}


// ============================
// Consent + email extraction
// ============================

function extractConsent_(sections) {
  // Find the consent row by label contains
  for (const sec of sections) {
    for (const row of sec.rows) {
      const l = (row.label || "").toLowerCase();
      if (l.includes("i agree") && l.includes("contact")) {
        const v = (row.value || "").toString().trim().toLowerCase();
        return (v === "yes") ? "yes" : "no";
      }
    }
  }
  return "no";
}

function extractEmail_(sections) {
  // Find the first row whose label includes "email" and looks like an email
  for (const sec of sections) {
    for (const row of sec.rows) {
      const l = (row.label || "").toLowerCase();
      const v = (row.value || "").toString().trim();
      if (l.includes("email") && v.includes("@")) return v;
    }
  }
  return "";
}


// ============================
// Masking
// ============================

function maskSections_(sections, keywords) {
  for (const sec of sections) {
    for (const row of sec.rows) {
      const l = (row.label || "").toLowerCase();
      if (keywords.some(k => l.includes(k))) {
        row.value = ""; // wipe value
      }
    }
  }
}


// ============================
// Status storage (uses linked responses spreadsheet)
// ============================

function writeInitialStatus_(complaintId) {
  // This relies on the Form being linked to a response spreadsheet
  const ssId = FormApp.getActiveForm().getDestinationId();
  if (!ssId) throw new Error("This Form is not linked to a response spreadsheet.");

  const ss = SpreadsheetApp.openById(ssId);
  const statusSheet = ss.getSheetByName("Complaint_Status");
  if (!statusSheet) throw new Error("Complaint_Status sheet not found in response spreadsheet.");

  const now = new Date().toISOString();
  statusSheet.appendRow([complaintId, now, "Received", now, ""]);
}


// ============================
// GitHub dispatch
// ============================

function dispatchToGithub_(clientPayload) {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty("GITHUB_PAT");
  const owner = props.getProperty("REPO_OWNER");
  const repo  = props.getProperty("REPO_NAME");
  if (!token || !owner || !repo) {
    throw new Error("Missing Script Properties: GITHUB_PAT, REPO_OWNER, REPO_NAME");
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/dispatches`;
  const payload = {
    event_type: "complaint_submitted",
    client_payload: clientPayload
  };

  const res = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    headers: {
      Authorization: `token ${token}`,
      Accept: "application/vnd.github+json"
    },
    muteHttpExceptions: true
  });

  Logger.log("GitHub status: " + res.getResponseCode());
  Logger.log("GitHub body: " + res.getContentText());

  const code = res.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error(`GitHub dispatch failed (${code}): ${res.getContentText()}`);
  }
}


// ============================
// Complaint ID generator
// ============================

function buildComplaintId_() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  const hh = String(now.getHours()).padStart(2, "0");
  const mm = String(now.getMinutes()).padStart(2, "0");
  return `RN-${y}${m}${d}-${hh}${mm}`;
}
