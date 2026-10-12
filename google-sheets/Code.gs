/**
 * SHACMAN PARTS: приём заявок с сайта в Google Sheets.
 * Развёртывание: см. SETUP.md в этой же папке.
 */

// Название листа, куда пишутся заявки (создастся автоматически).
var SHEET_NAME = 'Заявки';

// Необязательно: адрес для уведомления о новой заявке. Оставьте '' чтобы отключить.
var NOTIFY_EMAIL = '';

var HEADERS = ['Дата', 'Грузовик', 'Год', 'Запчасть', 'Категория', 'Комментарий', 'Способ связи', 'Контакт', 'Страница'];

function doPost(e) {
  try {
    var data = JSON.parse((e && e.postData && e.postData.contents) || '{}');

    // Ловушка для ботов: в скрытое поле люди ничего не вводят.
    if (data.website) return reply_({ ok: true });

    if (!clean_(data.truck) || !clean_(data.part) || !clean_(data.contact)) {
      return reply_({ ok: false, error: 'missing fields' });
    }

    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      var ss = SpreadsheetApp.getActiveSpreadsheet();
      var sheet = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
      if (sheet.getLastRow() === 0) {
        sheet.appendRow(HEADERS);
        sheet.setFrozenRows(1);
        sheet.getRange(1, 1, 1, HEADERS.length).setFontWeight('bold');
      }
      sheet.appendRow([
        new Date(),
        clean_(data.truck),
        clean_(data.year),
        clean_(data.part),
        clean_(data.category),
        clean_(data.comment),
        clean_(data.method),
        clean_(data.contact),
        clean_(data.page)
      ]);
    } finally {
      lock.releaseLock();
    }

    if (NOTIFY_EMAIL) {
      MailApp.sendEmail(
        NOTIFY_EMAIL,
        'Новая заявка SHACMAN PARTS',
        'Грузовик: ' + clean_(data.truck) + '\n' +
        'Запчасть: ' + clean_(data.part) + '\n' +
        'Контакт (' + clean_(data.method) + '): ' + clean_(data.contact)
      );
    }
    return reply_({ ok: true });
  } catch (err) {
    return reply_({ ok: false, error: String(err) });
  }
}

// Проверка в браузере: открытие ссылки /exec должно показать этот ответ.
function doGet() {
  return reply_({ ok: true, service: 'shacman-parts-requests' });
}

// Обрезаем длину и не даём тексту стать формулой (=, +, -, @ в начале ячейки).
function clean_(value) {
  var text = String(value == null ? '' : value).replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, 1000);
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
