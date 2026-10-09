"""STAGE 2 - Extract the reference product page: HTML of the two blocks (gallery + buy box) and the CSS that is
ACTUALLY USED by them (rules filtered against the real elements).

  py -3 extract_page.py <url> <work-dir> [gallery-selector] [buybox-selector]

Default selectors match Chinese storefront platforms (Shoplazza-style): #product-gallery-wrap / #product-form-wrap.
Shopify (Dawn-like themes): '.product__media-wrapper' / '.product__info-wrapper' - open DevTools and find the two
blocks that fully wrap [images] and [title, price, quantity, buy buttons, description].
Runs at PHONE size (390px) because most paid-social traffic is mobile.

IMPORTANT: run it while the reference store's cart is EMPTY - otherwise "Buy 2"-style buttons get captured in their
"added" state (a div, not a button) and do nothing in the rebuild.

Output in <work-dir>: used.css (filtered CSS), gallery.html, form.html,
meta.json (root font size, body font/colors, image list, stylesheets blocked by CORS)."""
import asyncio
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cdp import Chrome  # noqa: E402

URL, OUT = sys.argv[1], pathlib.Path(sys.argv[2])
G_SEL = sys.argv[3] if len(sys.argv) > 3 else "#product-gallery-wrap"
F_SEL = sys.argv[4] if len(sys.argv) > 4 else "#product-form-wrap"
OUT.mkdir(parents=True, exist_ok=True)

JS = r"""((G,F)=>{
const wraps=[document.querySelector(G),document.querySelector(F)];
if(!wraps[0]||!wraps[1]) return JSON.stringify({error:'blocks not found: '+G+' / '+F});
const rel=el=>wraps.some(w=>w.contains(el)||el.contains(w));
// strip pseudo-classes/elements so querySelector works; keep the rule if a matching element is inside the 2 blocks
const strip=s=>s.replace(/::?(before|after|placeholder|selection|marker|backdrop|-webkit-[a-z-]+|-moz-[a-z-]+|-ms-[a-z-]+)(\([^)]*\))?/g,'')
  .replace(/:(hover|focus|active|visited|link|focus-within|focus-visible|checked|disabled|enabled|empty|first-child|last-child|only-child|nth-child\([^)]*\)|nth-last-child\([^)]*\)|nth-of-type\([^)]*\)|first-of-type|last-of-type|not\([^)]*\)|is\([^)]*\)|where\([^)]*\)|root)/g,m=>m===':root'?'html':'');
const cache=new Map();
function test(sel){sel=sel.trim(); if(cache.has(sel))return cache.get(sel); let s=strip(sel).trim(); let ok=false;
  if(!s||/^[>+~\s*]*$/.test(s)) ok=true; else { try{ for(const el of document.querySelectorAll(s)){ if(rel(el)){ok=true;break} } }catch(e){ok=false} }
  cache.set(sel,ok); return ok}
function walk(rules){let out='';for(const r of rules){
  if(r.type===1){const ps=r.selectorText.split(/,(?![^()]*\))/).filter(test); if(ps.length) out+=ps.join(',')+'{'+r.style.cssText+'}\n'}
  else if(r.type===4){const i=walk(r.cssRules); if(i) out+='@media '+r.conditionText+'{\n'+i+'}\n'}
  else if(r.type===12){const i=walk(r.cssRules); if(i) out+='@supports '+r.conditionText+'{\n'+i+'}\n'}
  else if(r.type===5||r.type===7) out+=r.cssText+'\n';}   // keep @font-face and @keyframes as-is
 return out}
let css='',skip=[];
for(const sh of document.styleSheets){ try{ css+=walk(sh.cssRules) }catch(e){ skip.push(sh.href) } }
// HTML: lazy data-src -> src, drop scripts, open the shadow root of rich-content web components (ws-rich-content)
function html(el){const c=el.cloneNode(true);
  c.querySelectorAll('script,noscript,iframe,shop-pay-payment-request-button').forEach(x=>x.remove());
  c.querySelectorAll('img').forEach(i=>{const d=i.getAttribute('data-src')||i.getAttribute('data-original'); if(d&&(!i.getAttribute('src')||i.getAttribute('src').startsWith('data:'))) i.setAttribute('src',d); i.removeAttribute('data-srcset'); i.removeAttribute('srcset'); i.setAttribute('loading','lazy')});
  const orig=el.querySelectorAll('ws-rich-content'); const cl=c.querySelectorAll('ws-rich-content');
  orig.forEach((o,k)=>{const n=document.createElement('div'); n.className='product-description default_css'; n.innerHTML=o.shadowRoot?o.shadowRoot.innerHTML:o.innerHTML; cl[k].replaceWith(n)});
  return c.outerHTML}
const g=html(wraps[0]), f=html(wraps[1]);
const bs=getComputedStyle(document.body);
const imgs=[...new Set([...(g+f).matchAll(/https?:\/\/[^"'\s)]+\.(?:png|jpe?g|gif|webp|svg)/gi)].map(m=>m[0]))];
return JSON.stringify({css,skip,g,f,rootFont:getComputedStyle(document.documentElement).fontSize,bodyFont:bs.fontFamily,bodyColor:bs.color,bodyBg:bs.backgroundColor,imgs});
})(%s,%s)"""


async def main():
    ch = Chrome()
    await ch.open_tab()
    try:
        await ch.viewport(390, 844, True)
        await ch.goto(URL)
        await asyncio.sleep(10)
        await ch.scroll_all(500, 0.4)
        d = json.loads(await ch.js(JS % (json.dumps(G_SEL), json.dumps(F_SEL)), timeout=180))
    finally:
        await ch.close()
    if d.get("error"):
        sys.exit(d["error"])
    (OUT / "used.css").write_text(d["css"], encoding="utf-8", newline="\n")
    (OUT / "gallery.html").write_text(d["g"], encoding="utf-8", newline="\n")
    (OUT / "form.html").write_text(d["f"], encoding="utf-8", newline="\n")
    meta = {k: d[k] for k in ("skip", "rootFont", "bodyFont", "bodyColor", "bodyBg", "imgs")}
    (OUT / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("css", len(d["css"]), "| gallery", len(d["g"]), "| form", len(d["f"]), "| images", len(d["imgs"]),
          "| root font", d["rootFont"], "| CORS-blocked stylesheets:", d["skip"])

asyncio.run(main())
