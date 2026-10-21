/**
 * FM Pulse UAE — contact form backend (Google Apps Script).
 * Receives the website's Contact Us form, emails the message to the owner,
 * and sends the visitor an acknowledgment from the owner's Gmail.
 *
 * Deploy: Deploy → New deployment → Web app → Execute as: Me → Who has access: Anyone.
 */

const OWNER = 'ananader1@gmail.com';
const SITE = 'FM Pulse UAE';
const SIGNATURE = 'Anas Nader';
const MAX_PER_DAY = 40;      // all visitors combined (free Gmail allows ~100 recipients/day)
const MAX_PER_SENDER = 3;    // per visitor email address per day

function doPost(e) {
  try {
    const d = JSON.parse((e && e.postData && e.postData.contents) || '{}');

    // Honeypot: bots fill the hidden "website" field. Pretend success, send nothing.
    if (d.website) return out({ ok: true });

    const name = clean(d.name, 80);
    const email = clean(d.email, 120).toLowerCase();
    const subject = clean(d.subject, 120) || 'Suggestion';
    const message = String(d.message || '').slice(0, 4000).trim();

    if (!/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]{2,}$/.test(email)) {
      return out({ ok: false, error: 'Please enter a valid email address.' });
    }
    if (message.length < 5) {
      return out({ ok: false, error: 'Please write a short message.' });
    }

    const limit = checkLimits(email);
    if (limit) return out({ ok: false, error: limit });

    // 1) The message, to the owner. Reply goes straight to the visitor.
    GmailApp.sendEmail(
      OWNER,
      '[' + SITE + '] ' + subject,
      'New message from the ' + SITE + ' contact form\n\n' +
        'Name:  ' + (name || '(not given)') + '\n' +
        'Email: ' + email + '\n' +
        'Subject: ' + subject + '\n\n' +
        message + '\n',
      { replyTo: email, name: SITE + ' contact form' }
    );

    // 2) Acknowledgment, to the visitor. Deliberately generic: it never repeats
    //    the visitor's text, so the form cannot be used to send spam to others.
    GmailApp.sendEmail(
      email,
      'Thank you for contacting ' + SITE,
      'Hello,\n\n' +
        'Thank you for your message to ' + SITE + '. It has reached me and I will ' +
        'read it personally. If a reply is needed, I will get back to you at this address.\n\n' +
        'Your suggestions help decide which companies, services and news sources the ' +
        'app covers next.\n\n' +
        'Best regards,\n' + SIGNATURE + '\n' + SITE + '\n',
      { name: SIGNATURE + ' – ' + SITE, replyTo: OWNER }
    );

    return out({ ok: true });
  } catch (err) {
    console.error(err);
    return out({ ok: false, error: 'Sending failed. Please email ' + OWNER + ' directly.' });
  }
}

// Opening the web app URL in a browser shows this, which confirms the deployment works.
function doGet() {
  return out({ ok: true, service: SITE + ' contact form' });
}

function checkLimits(email) {
  const lock = LockService.getScriptLock();
  lock.waitLock(5000);
  try {
    const props = PropertiesService.getScriptProperties();
    const day = Utilities.formatDate(new Date(), 'Asia/Dubai', 'yyyy-MM-dd');
    if (props.getProperty('day') !== day) {   // new day: clear yesterday's counters
      props.deleteAllProperties();
      props.setProperty('day', day);
    }
    const total = Number(props.getProperty('total') || 0);
    const key = 's:' + email;
    const mine = Number(props.getProperty(key) || 0);
    if (total >= MAX_PER_DAY) return 'The contact form is busy today. Please try again tomorrow.';
    if (mine >= MAX_PER_SENDER) return 'You have already sent several messages today. Thank you!';
    props.setProperty('total', String(total + 1));
    props.setProperty(key, String(mine + 1));
    return '';
  } finally {
    lock.releaseLock();
  }
}

function clean(v, max) {
  return String(v || '').replace(/[\r\n\t]+/g, ' ').trim().slice(0, max);
}

function out(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// Run this once from the editor (select "authorize" → Run) to grant Gmail permission.
function authorize() {
  GmailApp.getAliases();
}
