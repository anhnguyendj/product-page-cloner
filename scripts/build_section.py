"""STAGES 3-4 - Assemble the extracted page into Shopify theme files (Shadow DOM, content embedded inline, renders
instantly - no fetch, no blank flash).

  py -3 build_section.py <work-dir>

Reads from <work-dir>: used.css, gallery.html, form.html, meta.json (from extract_page.py) + clone-config.json
(you fill it in; see clone-config.example.json). Optionally reads store.json (work dir first, then the skill root).

Writes to <work-dir>/out/:
  sections/<P>-<slug>.liquid           thin section: preload, fonts link, host div, variants JSON, <template>, script
  snippets/<P>-<slug>-c1..cN.liquid    CSS chunks   (each <= 19KB, wrapped in {% raw %})
  snippets/<P>-<slug>-h1..hN.liquid    HTML chunks  (each <= 19KB)
  snippets/<P>-<slug>-j1..jN.liquid    runtime JS chunks (each <= 19KB)
  assets/<P>-<slug>-fonts.css          @font-face in the MAIN document (@font-face inside a shadow root is ignored)
  templates/product.<P>-<slug>.json    main (+ related) (+ real-data social proof) + cart drawer (+ exit popup)
  fonts/                               original font files downloaded -> upload to Shopify Files, fill font_urls
  test.html                            open locally to eyeball before uploading
  manifest.txt                         every output file with size + md5 (LF line endings) to compare with
                                       Shopify's checksumMd5 after upload
<P> is store.json "prefix" (default "ppc").

Why 19KB chunks: themeFilesUpsert with body type URL is unreliable (reports success, file unchanged), so files are
uploaded as TEXT, which has to pass through a tool call - keep every file small enough to send intact.
"""
import hashlib
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

W = pathlib.Path(sys.argv[1])
OUT = W / "out"
for p in ("sections", "snippets", "assets", "templates", "fonts"):
    (OUT / p).mkdir(parents=True, exist_ok=True)
HERE = pathlib.Path(__file__).parent
SKILL = HERE.parent


def load_json(*paths):
    for p in paths:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return {}


C = load_json(W / "clone-config.json")
if not C:
    sys.exit(f"missing {W / 'clone-config.json'} (copy clone-config.example.json and fill it in)")
STORE = load_json(W / "store.json", SKILL / "store.json")
P = STORE.get("prefix") or "ppc"
SLUG = C["slug"]
SRC = C["source_url"]
IMAGE_MAP = C.get("image_map", {})   # {"reference image URL without query": "your Shopify CDN URL"}
FONT_URLS = C.get("font_urls", {})   # {"font file name": "your Shopify CDN URL"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36"


def write(path, text):
    """All theme files are written UTF-8 with LF endings so md5 matches what Shopify stores."""
    path.write_text(text, encoding="utf-8", newline="\n")


def swap_images(s):
    """Every reference-store image URL -> your Shopify CDN URL (uploaded in stage 1/3). Unmapped ones stay and are reported."""
    def f(m):
        u = m.group(0)
        return IMAGE_MAP.get(u.split("?")[0], u)
    return re.sub(r"https?://[^\"'\s)]+\.(?:png|jpe?g|gif|webp|svg)(?:\?[^\"'\s)]*)?", f, s)


# ---------- CSS ----------
css = (W / "used.css").read_text(encoding="utf-8")
fonts = [ln for ln in css.split("\n") if ln.startswith("@font-face")]
css = "\n".join(ln for ln in css.split("\n") if not ln.startswith("@font-face"))


def map_selector(sel):
    out = []
    for part in sel.split(","):
        p = re.sub(r"(^|[\s>+~])html(?=$|[\s>+~.:#\[])", r"\1.ppc-html", part)
        p = re.sub(r"(^|[\s>+~])body(?=$|[\s>+~.:#\[])", r"\1.ppc-body", p)
        out.append(p.replace(":root", ".ppc-html"))
    return ",".join(out)


lines = []
for line in css.split("\n"):
    if line and not line.startswith("@") and line != "}" and "{" in line:
        sel, rest = line.split("{", 1)
        line = map_selector(sel) + "{" + rest
    lines.append(line)
css = "\n".join(lines)
# rem inside a shadow root still resolves against the THEME's <html> font-size -> convert to px using the
# reference page's root size. (rem inside inline style="" attributes is NOT converted - see SKILL.md, Shopify fixes.)
meta = load_json(W / "meta.json")
root_px = float(re.sub(r"[^\d.]", "", meta.get("rootFont", "16px")) or 16)
css = re.sub(r"(-?\d*\.?\d+)rem\b", lambda m: f"{round(float(m.group(1)) * root_px, 3)}px", css)
css = swap_images(css)
css += (SKILL / "templates" / "clone-base.css").read_text(encoding="utf-8")

# ---------- FONTS: download, rewrite URLs ----------
ff = []
for f in fonts:
    def map_font(m):
        if m.group(1).startswith("data:"):
            return m.group(0)  # already inlined base64
        u = urllib.parse.urljoin(SRC, m.group(1))
        name = pathlib.Path(urllib.parse.urlparse(u).path).name
        if name in FONT_URLS:
            return f'url("{FONT_URLS[name]}")'
        dest = OUT / "fonts" / name
        if not dest.exists():
            try:
                req = urllib.request.Request(u, headers={"User-Agent": UA})
                dest.write_bytes(urllib.request.urlopen(req, timeout=30).read())
            except Exception as e:  # noqa: BLE001
                print("  could not download font", u, e)
        return f'url("{u}")'  # temporary: original URL; upload to Shopify Files and fill font_urls to avoid CORS
    f = re.sub(r"""url\(\s*['"]?([^'")]+)['"]?\s*\)""", map_font, f)
    if "font-display" not in f:
        f = f.replace("{", "{font-display:swap;", 1)
    ff.append(f)
write(OUT / "assets" / f"{P}-{SLUG}-fonts.css", "\n".join(dict.fromkeys(ff)))
if any("url(\"http" in x and "cdn.shopify.com" not in x for x in ff):
    print("  note: some fonts still point at the reference store - upload them (fonts/) and fill font_urls")

# ---------- HTML ----------
form = swap_images((W / "form.html").read_text(encoding="utf-8"))
for rule in C.get("html_fixes", []):  # [pattern, replacement] or {"pattern","replace","why"}
    if isinstance(rule, dict):
        pat, rep = rule["pattern"], rule.get("replace", "")
    else:
        pat, rep = rule
    form, n = re.subn(pat, rep, form, flags=re.S)
    print(f"  html_fixes {pat[:50]!r}: {n} match(es)")
gal = C.get("gallery", [])  # your CDN URLs in the reference page's image order
if gal:  # rebuilt gallery: horizontal scroll-snap + counter + thumbnails (replaces their swiper/JS)
    def q(u):
        return "&" if "?" in u else "?"
    slides = "".join(
        f'<img src="{u}{q(u)}width=900" alt="" loading="{"eager" if i == 0 else "lazy"}"'
        + (' fetchpriority="high"' if i == 0 else "") + ">"
        for i, u in enumerate(gal))
    thumbs = "".join(f'<img src="{u}{q(u)}width=150" data-i="{i}" class="{"on" if i == 0 else ""}" alt="">'
                     for i, u in enumerate(gal))
    gallery = (f'<div id="product-gallery-wrap" class="{C.get("gallery_class", "product-left")}"><div class="ppc-gal">'
               f'<div class="ppc-track">{slides}</div><div class="ppc-count"><span data-ppc="idx">1</span> / {len(gal)}</div></div>'
               f'<div class="ppc-thumbs">{thumbs}</div></div>')
else:
    gallery = swap_images((W / "gallery.html").read_text(encoding="utf-8"))
w_open, w_close = C.get("wrappers", ['<div class="container d-flex align-items-start">', "</div>"])
body = f'<div class="ppc-html"><div class="ppc-body">{w_open}{gallery}{form}{w_close}</div></div>'

# ---------- pre-upload warnings ----------
visible = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", body, flags=re.S)
cjk = sorted(set(re.findall(r"[⺀-鿿豈-﫿＀-￯　-〿]+", visible)))
if cjk:
    print("  !! CJK TEXT left in the HTML -> remove/translate with html_fixes before uploading:", cjk[:20])
text_emoji = sorted(set(re.findall("[\U0001F5BC❤✔☀✈☎✂⚠♥☺☃✏✉✖](?!️)", visible)))
if text_emoji:
    print("  note: text-style emoji without U+FE0F (runtime adds it, but check by eye at 390px):", text_emoji)
left = sorted(set(re.findall(r"https?://(?!cdn\.shopify\.com)[^\"'\s)]+\.(?:png|jpe?g|gif|webp)", body + css)))
if left:
    print("  WARNING:", len(left), "image(s) still point at the reference store (not uploaded / not in image_map):", left[:5])
src_host = urllib.parse.urlparse(SRC).netloc.lower()
src_name = max(src_host.split(".")[:-1] or [""], key=len)  # longest label except the TLD, e.g. "brandname"
if len(src_name) > 3 and src_name in visible.lower():
    print(f"  WARNING: the reference store name/domain ('{src_name}') still appears in the visible HTML - remove it with html_fixes")
for word in ("trustpilot", "judge.me verified", "designed in", "only 1 left", "people are viewing", "visitors",
             "recently purchased", "left in stock", "sold in the last"):
    if word in visible.lower():
        print(f"  CHECK: '{word}' found - third-party badge / scarcity / origin claim? Remove it; real stock / real "
              "recent orders come from the ppc-social-proof section instead (SKILL.md guardrails)")

# ---------- drop unused @keyframes (one real case: 312 of them, CSS 88KB -> 31KB) ----------
used_anim = " ".join(set(re.findall(r"animation(?:-name)?\s*:[^;}]*", css)))


def drop_kf(m):
    return m.group(0) if re.search(r"(?<![\w-])" + re.escape(m.group(1)) + r"(?![\w-])", used_anim) else ""


css = re.sub(r"@(?:-webkit-)?keyframes\s+([\w-]+)\s*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}\n?", drop_kf, css)

# ---------- SNIPPETS (<= 19KB each) ----------
assert "{% endraw %}" not in body + css, "content contains '{% endraw %}' -> must be split manually"


def chunk(s, limit=19000):
    pieces = []
    for ln in s.splitlines(keepends=True):  # very long single-line HTML -> split before each '<'
        pieces += re.split(r"(?=<)", ln) if len(ln) > limit else [ln]
    out, cur = [], ""
    for m in pieces:
        if cur and len(cur) + len(m) > limit:
            out.append(cur)
            cur = ""
        cur += m
    return [x for x in out + [cur] if x]


snips = []
for kind, content in (("c", css), ("h", body)):
    for i, part in enumerate(chunk(content), 1):
        name = f"{P}-{SLUG}-{kind}{i}"
        snips.append(name)
        write(OUT / "snippets" / f"{name}.liquid", "{% raw %}" + part + "{% endraw %}")
css_r = "".join(f"{{% render '{t}' %}}" for t in snips if t.startswith(f"{P}-{SLUG}-c"))
html_r = "".join(f"{{% render '{t}' %}}" for t in snips if t.startswith(f"{P}-{SLUG}-h"))
JS = (SKILL / "templates" / "clone-runtime.js").read_text(encoding="utf-8")
js_snips = []  # runtime JS is its own snippet set (inlined in the section it pushed the section over the TEXT limit)
for i, part in enumerate(chunk(JS), 1):
    name = f"{P}-{SLUG}-j{i}"
    js_snips.append(name)
    write(OUT / "snippets" / f"{name}.liquid", "{% raw %}" + part + "{% endraw %}")

# mix & match (multi-style products): "mix": {"tiers": [[1,0,""],[2,5,""],[3,10,"MOST POPULAR"],[4,20,"BEST VALUE"]], "default_tier": 2}
MIX = C.get("mix")
# Real Shop Pay button + installments line of YOUR store. The reference store's buttons belong to THEIR store and
# cannot work when copied. Shopify renders yours via {{ form | payment_button }} / payment_terms, placed in the
# LIGHT DOM of #ppc-root (Shopify's scripts cannot reach into a shadow root) and projected into place with <slot>:
# html_fixes replaces their express-checkout block with <slot name="ppc-pay"></slot> and the
# installments form with <slot name="ppc-terms"></slot>.
SHOP_PAY = C.get("shop_pay")
pay_html = ("<div slot=\"ppc-terms\">{%- form 'product', product -%}<input type=\"hidden\" name=\"id\" value=\"{{ product.selected_or_first_available_variant.id }}\">"
            "{{ form | payment_terms }}{%- endform -%}</div>"
            "<div slot=\"ppc-pay\" style=\"margin-top:10px\">{%- form 'product', product -%}<input type=\"hidden\" name=\"id\" value=\"{{ product.selected_or_first_available_variant.id }}\">"
            "{{ form | payment_button }}{%- endform -%}</div>"
            "<style>#ppc-root .shopify-payment-button__more-options{display:none}#ppc-root shopify-payment-terms{font-size:14px}</style>") if SHOP_PAY else ""
mix_attr = (" data-mix=\"1\" data-tiers='" + json.dumps(MIX["tiers"], ensure_ascii=False) + "' data-default-tier=\""
            + str(MIX.get("default_tier", 0)) + "\"") if MIX else ""
preload = f'<link rel="preload" as="image" href="{gal[0]}{"&" if "?" in gal[0] else "?"}width=900" fetchpriority="high">\n' if gal else ""
sec = ("{%- comment -%} product-page-cloner: rebuilt layout, content embedded inline (renders instantly). {%- endcomment -%}\n"
       + preload
       + f"<link rel=\"stylesheet\" href=\"{{{{ '{P}-{SLUG}-fonts.css' | asset_url }}}}\" media=\"print\" onload=\"this.media='all'\">\n"
       + '<div id="ppc-root" data-variant="{{ product.selected_or_first_available_variant.id }}"' + mix_attr + ' style="display:block">' + pay_html + '</div>\n'
       + '<script type="application/json" id="ppc-variants">{{ product.variants | json }}</script>\n'
       + f'<template id="ppc-tpl"><style>{css_r}</style>{html_r}</template>\n'
       + "<script>" + "".join(f"{{% render '{t}' %}}" for t in js_snips) + "</script>\n"
       + '{% schema %}\n{"name":"PPC ' + SLUG + '","settings":[]}\n{% endschema %}\n')
write(OUT / "sections" / f"{P}-{SLUG}.liquid", sec)
print("snippets:", ", ".join(f"{t} {len((OUT / 'snippets' / (t + '.liquid')).read_text(encoding='utf-8')) // 1024}KB" for t in snips + js_snips))

# ---------- TEMPLATE ----------
sections = {"main": {"type": f"{P}-{SLUG}", "settings": {}}}
order = ["main"]
if C.get("related", True):
    sections["related"] = {"type": "ppc-related", "settings": {}}
    order.append("related")
SP = C.get("social_proof")
if SP is not None and SP is not False:
    sections["proof"] = {"type": "ppc-social-proof", "settings": SP if isinstance(SP, dict) else {}}
    order.append("proof")
drawer = {"insurance_handle": STORE.get("insurance_product_handle") or "", "insurance_percent": STORE.get("insurance_percent", 5)}
drawer.update(C.get("drawer", {}))
sections["drawer"] = {"type": "ppc-cart-drawer", "settings": drawer}
order.append("drawer")
EXIT = C.get("exit_popup")
if EXIT:
    ex = {"brand": STORE.get("brand_name", ""), "klaviyo_key": STORE.get("klaviyo_public_key") or ""}
    ex.update(EXIT)
    if not ex.get("brand") or not ex.get("code"):
        print("  WARNING: exit_popup needs brand (store.json brand_name) and code - popup will not render without them")
    sections["exit"] = {"type": "ppc-exit-popup", "settings": ex}
    order.append("exit")
write(OUT / "templates" / f"product.{P}-{SLUG}.json", json.dumps({"sections": sections, "order": order}, ensure_ascii=False, indent=1))

# ---------- local test page ----------
test = ("<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
        "<style>" + "\n".join(ff) + "</style></head><body style='margin:0'>"
        "<div id='ppc-root' data-variant='1'></div><template id='ppc-tpl'><style>" + css + "</style>" + body
        + "</template><script>" + JS + "</script></body></html>")
write(OUT / "test.html", test)

# ---------- manifest: size + md5 (LF) for post-upload verification ----------
rows = []
for f in sorted(OUT.rglob("*")):
    if f.is_file() and f.parent.name in ("sections", "snippets", "assets", "templates"):
        b = f.read_bytes().replace(b"\r\n", b"\n")
        rows.append(f"{f.relative_to(OUT).as_posix()}\t{len(b)}\t{hashlib.md5(b).hexdigest()}")
write(OUT / "manifest.txt", "\n".join(rows) + "\n")
big = [r for r in rows if int(r.split("\t")[1]) > 19500 and not r.startswith("assets/")]
if big:
    print("  WARNING: files over ~19KB (TEXT upload may be cut):", big)
print("section", len(sec) // 1024, "KB | css", len(css) // 1024, "KB | html", len(body) // 1024, "KB | fonts", len(ff),
      "| files", len(rows), "| out:", OUT)
