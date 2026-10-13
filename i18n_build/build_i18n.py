"""Embed ru / kk / en translations into index.html (idempotent).

Run from anywhere:  python i18n_build/build_i18n.py
"""
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from translations import T  # noqa: E402

PATH = os.path.join(ROOT, 'index.html')
s = open(PATH, encoding='utf8').read()

T.pop('Телефон ', None)
T.setdefault('Сайт', ('Сайт', 'Website'))
T.setdefault('ҚАЗ', ('ҚАЗ', 'ҚАЗ'))

# ---------- coverage check ----------
body = s[s.index('<header class="hdr"'):]
body = re.sub(r'<script.*?</script>|<style.*?</style>', '', body, flags=re.S)
segs = set()
for m in re.finditer(r'>([^<>]+)<', body):
    t = re.sub(r'\s+', ' ', html.unescape(m.group(1))).strip()
    if t and re.search(r'[А-Яа-яЁё]', t):
        segs.add(t)
for m in re.finditer(r'\b(placeholder|aria-label|alt)="([^"]+)"', body):
    t = html.unescape(m.group(2)).strip()
    if re.search(r'[А-Яа-яЁё]', t):
        segs.add(t)
desc = re.search(r'<meta name="description" content="([^"]+)"', s)
if desc:
    segs.add(desc.group(1))
missing = sorted(x for x in segs if x not in T)
if missing:
    print('MISSING translations:')
    for x in missing:
        print('  -', x)
    sys.exit(1)
print('coverage ok:', len(segs), 'strings')

I18N = {k: {'kk': v[0], 'en': v[1]} for k, v in T.items()}

# ---------- JS block ----------
JS_START, JS_END = '/* i18n:start */', '/* i18n:end */'
js_block = JS_START + r"""
  var I18N=%s;
  var CAT_RU={engine:'Двигатель и комплектующие',transmission:'Трансмиссия и сцепление',brakes:'Тормозная система',suspension:'Подвеска и ходовая часть',electrics:'Электрика и датчики',filters:'Фильтры и расходные материалы'};
  var META_RU=%s;
  var LANG='ru',i18nText=[],i18nAttr=[];
  function norm(x){return x.replace(/\s+/g,' ').trim()}
  function T(ru){var e=I18N[ru];return (e&&e[LANG])||ru}
  function i18nCollect(){
    var w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,null),n;
    while((n=w.nextNode())){
      var p=n.parentNode;if(!p||/^(SCRIPT|STYLE)$/i.test(p.nodeName))continue;
      var k=norm(n.nodeValue);
      if(k&&I18N[k])i18nText.push({n:n,k:k,pre:n.nodeValue.match(/^\s*/)[0],post:n.nodeValue.match(/\s*$/)[0]});
    }
    ['placeholder','aria-label','alt'].forEach(function(a){
      $$('['+a+']').forEach(function(el){var k=norm(el.getAttribute(a));if(I18N[k])i18nAttr.push({el:el,a:a,k:k})});
    });
  }
  function contactLabel(){$('label[for=contact]').textContent=T(method==='WhatsApp'?'Номер WhatsApp':'Телефон')}
  function i18nApply(lang){
    LANG=lang;
    root.setAttribute('lang',lang);
    i18nText.forEach(function(r){var e=I18N[r.k];r.n.nodeValue=r.pre+((e&&e[lang])||r.k)+r.post});
    i18nAttr.forEach(function(r){var e=I18N[r.k];r.el.setAttribute(r.a,(e&&e[lang])||r.k)});
    var m=document.querySelector('meta[name=description]');if(m)m.setAttribute('content',T(META_RU));
    $$('a[href^="https://wa.me/"]').forEach(function(a){
      if(a.__ru===undefined){var q=a.getAttribute('href').split('?text=')[1];a.__ru=q?decodeURIComponent(q):''}
      a.setAttribute('href',a.getAttribute('href').split('?')[0]+'?text='+encodeURIComponent(T(a.__ru)));
    });
    $$('.lang button').forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-lang')===lang))});
    try{localStorage.setItem('sp-lang',lang)}catch(e){}
  }
""" % (json.dumps(I18N, ensure_ascii=False), json.dumps(desc.group(1) if desc else '', ensure_ascii=False)) + '  ' + JS_END

INIT_START, INIT_END = '/* i18n-init:start */', '/* i18n-init:end */'
init_block = INIT_START + r"""
  i18nCollect();
  (function(){
    var saved=null;try{saved=localStorage.getItem('sp-lang')}catch(e){}
    var navLang=(navigator.language||'ru').toLowerCase();
    var lang=saved||(navLang.indexOf('kk')===0?'kk':navLang.indexOf('en')===0?'en':'ru');
    if(['ru','kk','en'].indexOf(lang)<0)lang='ru';
    if(lang!=='ru'){i18nApply(lang);contactLabel()}
    $$('.lang button').forEach(function(b){
      b.addEventListener('click',function(){
        i18nApply(b.getAttribute('data-lang'));contactLabel();
        var open=$('#nav').classList.contains('open');
        $('#burger').setAttribute('aria-label',T(open?'Закрыть меню':'Открыть меню'));
      });
    });
    $$('.lang button').forEach(function(b){b.setAttribute('aria-pressed',String(b.getAttribute('data-lang')===lang))});
  })();
  """ + INIT_END


def put(s, start, end, block, anchor, after=True):
    if start in s:
        return re.sub(re.escape(start) + r'.*?' + re.escape(end), lambda m: block, s, count=1, flags=re.S)
    assert anchor in s, 'anchor missing: ' + anchor[:60]
    i = s.index(anchor)
    if after:
        i += len(anchor)
    return s[:i] + '\n  ' + block + '\n' + s[i:]


s = put(s, JS_START, JS_END, js_block, "var SHEETS_URL=window.SHACMAN_SHEETS_URL||'';")
s = put(s, INIT_START, INIT_END, init_block, "\n})();\n</script>", after=False)

# ---------- dynamic strings in the existing script ----------
def sub(old, new):
    global s
    if old in s:
        s = s.replace(old, new, 1)
    elif new not in s:
        raise SystemExit('cannot patch: ' + old[:80])


sub("$('label[for=contact]').textContent=method==='WhatsApp'?'Номер WhatsApp':'Телефон';", "contactLabel();")
sub("burger.setAttribute('aria-label',open?'Закрыть меню':'Открыть меню');", "burger.setAttribute('aria-label',T(open?'Закрыть меню':'Открыть меню'));")
sub("$('#doneTitle').textContent='Заявка принята';", "$('#doneTitle').textContent=T('Заявка принята');")
sub("$('#doneNote').textContent=sent?'Менеджер свяжется с вами в ближайшее время.':'Демонстрация: данные никуда не отправляются.';",
    "$('#doneNote').textContent=T(sent?'Менеджер свяжется с вами в ближайшее время.':'Демонстрация: данные никуда не отправляются.');")
sub("sendErr.textContent='Заявка только что была отправлена. Подождите несколько секунд и попробуйте снова.';",
    "sendErr.textContent=T('Заявка только что была отправлена. Подождите несколько секунд и попробуйте снова.');")
sub("sendErr.textContent='Не удалось отправить заявку. Проверьте интернет и попробуйте ещё раз или свяжитесь с менеджером.';",
    "sendErr.textContent=T('Не удалось отправить заявку. Проверьте интернет и попробуйте ещё раз или свяжитесь с менеджером.');")
sub("sendLbl.textContent='Отправляем…';", "sendLbl.textContent=T('Отправляем…');")
sub("sendLbl.textContent='Отправить заявку'", "sendLbl.textContent=T('Отправить заявку')")
sub("category:catSel.value?catSel.options[catSel.selectedIndex].text:'',", "category:catSel.value?(CAT_RU[catSel.value]||''):'',")

# ---------- switcher markup ----------
SW = '''      <div class="lang" role="group" aria-label="Язык / Language">
        <button type="button" data-lang="ru" aria-pressed="true">RU</button>
        <button type="button" data-lang="kk" aria-pressed="false">ҚАЗ</button>
        <button type="button" data-lang="en" aria-pressed="false">EN</button>
      </div>
'''
if 'class="lang"' not in s:
    anchor = '      <a class="btn btn-red" href="#request">Оставить заявку</a>\n    </nav>'
    assert anchor in s
    s = s.replace(anchor, SW + anchor, 1)

# ---------- css ----------
CSS_START, CSS_END = '/* i18n-css:start */', '/* i18n-css:end */'
css = CSS_START + """
.lang{display:inline-flex;border:1px solid var(--line)}
.lang button{border:0;background:transparent;color:#cfcbc0;padding:0 11px;min-height:44px;min-width:46px;font:500 12px/1 var(--f-mono);letter-spacing:.06em;cursor:pointer;transition:background .2s,color .2s}
.lang button+button{border-left:1px solid var(--line)}
.lang button:hover{color:#fff}
.lang button[aria-pressed=true]{background:var(--accent);color:var(--on-accent)}
.nav a.l,.wm small{white-space:nowrap}
html[lang=kk] .hero h1{font-size:clamp(2rem,3.5vw,3.5rem);line-height:1.06}
html[lang=en] .hero h1{font-size:clamp(2.2rem,4.2vw,4.1rem)}
@media (max-width:1400px){.nav{gap:20px}}
@media (max-width:1200px){.nav{gap:16px}.nav a.l{font-size:13px}}
@media (max-width:1100px){
  .nav{display:none;position:absolute;top:100%;left:0;right:0;flex-direction:column;align-items:stretch;gap:0;background:rgba(10,10,10,.98);border-bottom:1px solid var(--line);padding:8px var(--gutter) 24px}
  .nav.open{display:flex}
  .nav a.l{padding:16px 0;border-bottom:1px solid var(--line);font-size:17px}
  .nav .btn{margin-top:18px;min-height:52px}
  .burger{display:inline-flex}
}
.nav .lang{margin:0}
.req-list b{width:auto;min-width:56px;white-space:nowrap}
@media (max-width:1100px){.nav .lang{align-self:flex-start;margin-top:18px}.nav .lang+.btn{margin-top:14px}}
""" + CSS_END
if CSS_START in s:
    s = re.sub(re.escape(CSS_START) + r'.*?' + re.escape(CSS_END), lambda m: css, s, count=1, flags=re.S)
else:
    s = s.replace('\n/* Reveal */', '\n' + css + '\n/* Reveal */', 1)

open(PATH, 'w', encoding='utf8').write(s)
print('built')
