/**
 * 華さんのおすすめマップの「受け取り口」（Google Apps Script）
 * 華さんがページの「このまま送信する」を押すと、この口に文章が届く。
 *   ・スプレッドシートの「受信」シートに1行ずつ溜まる
 *   ・矢貫さんのGmailに、文章そのままのメールが届く
 * 使い方は hana_receiver_setup.md を見る。
 */
const SHEET_NAME = '受信';
const MAX_LEN = 20000;           // 長すぎる文章は受け付けない（いたずら対策）

function doPost(e) {
  let d = {};
  try { d = JSON.parse(e.postData.contents); }
  catch (_) { d = { text: String((e.postData && e.postData.contents) || '') }; }
  const text = String(d.text || '').slice(0, MAX_LEN);
  const who  = String(d.who  || '').slice(0, 40);
  if (!text.trim()) return ContentService.createTextOutput('empty');

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
  if (sh.getLastRow() === 0) sh.appendRow(['届いた日時', 'お名前', '文章', '端末']);
  sh.appendRow([new Date(), who, text, String(d.ua || '').slice(0, 120)]);

  try {
    MailApp.sendEmail(
      Session.getEffectiveUser().getEmail(),
      '【三浦A邸】おすすめマップに返事が届きました' + (who ? '（' + who + '）' : ''),
      (who ? who + 'さんから\n\n' : '') + text
    );
  } catch (_) { /* メールに失敗しても、シートには残る */ }
  return ContentService.createTextOutput('ok');
}

function doGet() { return ContentService.createTextOutput('ok'); }
