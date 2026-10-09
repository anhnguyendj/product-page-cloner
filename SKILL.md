---
name: product-page-cloner
description: "Rebuild a reference product page's LAYOUT and buying UX on the user's own Shopify store, pixel-faithful: gallery + buy box extracted at 390px with filtered CSS, embedded in a Shadow-DOM section, variants/swatches, mix & match quantity tiers, slide-in cart drawer, automatic quantity discounts, per-product shipping profile, optional shipping insurance, the reference's own sticky add-to-cart bar, real Shop Pay + installments, related products, optional exit-intent email popup. Works from Shopify stores and Chinese storefront platforms (Shoplazza-style). Always on a DUPLICATED unpublished theme; the user publishes. Use when the user says: \"clone this product page\", \"make my product page look like <url>\", \"rebuild this page on my Shopify store\", \"copy the layout / add to cart / cart drawer of this store\", \"same buy box as <url>\", \"mirror this PDP\". Stages 0-10: measure reference -> product -> extract -> images+fonts -> build section -> theme -> discounts -> cart drawer -> shipping -> insurance -> acceptance. Self-improving: reads and appends LEARNINGS.md / CASES.md / CHECKS.md every run."
---

# product-page-cloner

Rebuild a reference product page (any Shopify store, or Chinese platforms such as Shoplazza) on the user's OWN Shopify
store: same layout, same buying flow, same cart behaviour - with the user's own brand, products, media and offer.
The method copies the rendered HTML/CSS of two blocks (gallery + buy box) instead of "re-designing", so the result
matches to the pixel. A first run takes a day of discovery; following this skill it takes ~2-3 hours.

**Files**: `scripts/` (Python, run with `py -3` on Windows / `python3` elsewhere), `templates/` (theme files),
`store.example.json` -> `store.json` (store facts, gitignored), `clone-config.example.json` -> `<work>/clone-config.json`
(per clone, gitignored), `LEARNINGS.md`, `CASES.md`, `CHECKS.md` (the skill's memory - see last section).

**Tools needed**: Shopify Admin GraphQL (Shopify MCP `graphql_query` / `graphql_mutation`, or Admin API access) ·
a browser the agent can drive for reading pages (Claude in Chrome or similar) · a DEDICATED Chrome with remote
debugging for the scripts (`CDP_PORT`, default 9230; see `scripts/cdp.py` for the launch command) ·
Python 3 + `pip install websockets` (Pillow optional, for cropping/comparing screenshots).
Never borrow a Chrome instance that other automation is using: backgrounded tabs get throttled and silently break it.

---

## Before you start (mandatory, 2 minutes)

1. Read `LEARNINGS.md` (mistakes users already pointed out - do not repeat them), `CASES.md` (which branch this
   clone is), `CHECKS.md` (what acceptance means). Note the start time for the Run log.
2. Load `store.json` (skill root or work dir). Missing -> copy `store.example.json`, discover the IDs (below), ask the
   user only for what cannot be discovered (brand name, public domain, insurance yes/no).
3. Create a work dir (e.g. `work/<slug>/`, gitignored).

Discover IDs instead of hardcoding them:
```graphql
query { shop { name myshopifyDomain primaryDomain { host } paymentSettings { supportedDigitalWallets } }
  locations(first: 10) { nodes { id name isActive } }
  publications(first: 20) { nodes { id name } }            # "Online Store" -> online_store_publication_gid
  themes(first: 25) { nodes { id name role processing } } }  # role MAIN = live theme; count them (limit 20)
```

## Guardrails (non-negotiable - tell the user WHY when you remove something)

- **Mirror layout and UX only.** Never copy the reference store's name, logo, domain, trademarks, or brand assets.
  `build_section.py` warns if the reference name/domain survives; fix with `html_fixes`.
- **No third-party trust signals that are not yours**: rating widgets (Trustpilot, Judge.me...), review counts, star
  averages, "as seen on", certification badges. Remove them in `html_fixes`.
- **No fabricated claims**: fake "designed in <city>" origin, fake countdowns, fake stock counters ("only 3 left",
  "1,204 people viewing"), fake "recently purchased" notifications. Remove them; never add them. If the user insists,
  explain the consumer-protection and ad-platform risk and do not build it.
- **Product images and copy default to the user's OWN media and text.** Copying someone else's photos or
  descriptions is a copyright risk that the user must explicitly decide on and is responsible for - ask, do not assume.
- **Never write to the live (MAIN) theme.** Duplicate it, edit the copy, send a preview link; the user publishes.
- **Confirm before any Admin change that is live immediately**: automatic discounts, discount codes, delivery
  profiles, product status/publication, insurance product. State exactly what will change, then do it.
- **Never place orders or pay** when testing checkout. Read up to the shipping step and stop. Clear test carts
  (`/cart/clear.js`) on the user's store AND restore the reference store's cart afterwards. Never type personal data
  into someone else's checkout; if a test address is needed, ask the user and use an obviously fake one.
- Tests that hit an email platform: block the request (do not subscribe fake emails to a real list).
- Store-specific facts go in `store.json` / local notes only, never in the shared skill files.

---

## Stage 0 - MEASURE the reference (fill this table BEFORE touching Shopify)

Read text with JS (`document.body.innerText`), do not guess. Look at BOTH 390px and 1440px and wait 30 s.

| Item | How to measure |
|---|---|
| Price / compare-at | product page |
| Quantity tiers | "Buy more save more" block; note qty -> % |
| Cart tip lines per quantity | add 1, 2, 3, 4 items, read `/cart` ("Buy 1 more and save 5%" ...) |
| Cart footer | 1 item vs discounted: Subtotal / Discount / Total; line price = unit price? |
| Cart drawer on ADD TO CART | click for real, screenshot: side, header, buttons, colors |
| Shipping rates | checkout up to the Shipping step with 1 / 2 / 4 items: thresholds, method names, prices |
| Shipping insurance | checkout Shipping step: % of FULL or DISCOUNTED price (measure at >= 2 cart sizes), pre-ticked? texts |
| Announcement bar | text, colors, rotation |
| Sticky add-to-cart bar | at 390 and 1440, after scrolling past the buy button |
| Express checkout / installments | Shop Pay button, "Pay in N installments" line |
| Upsells / gifts / popups | scroll whole page, cart, checkout |
| Variants | option groups, values, which variant is a "bundle" (price > 2x the cheapest) |
| Items to REMOVE (guardrails) | third-party badges, review counts, origin claims, fake scarcity/social proof |
| Supplier facts | real size / weight / materials from YOUR supplier - copy states only what is true for your product |

Checkout tip: the reference checkout may reuse the browser's cookies and show a saved address. If a form must be
filled, ask the user first; select the country BEFORE typing the address; type the phone in `input[type=tel]`.
Close every tab you opened when done.

## Stage 1 - Product on Shopify

1. Create the product (`productCreate` / MCP `create-product`) with the USER'S media (`images: [{url, altText}]` -
   Shopify downloads URLs to its CDN). Start as `DRAFT`. SKU `<sku_prefix>-<slug>`, tag `<product_tag>`.
2. Description: the user's own copy (if they deliberately chose to reuse the reference text, that is their call -
   see guardrails). Rewrite any image URLs inside it to your CDN.
3. Image map: `product { media(first: 50) { nodes { ... on MediaImage { image { url } } } } }` -> fill
   `clone-config.json` `image_map` + `gallery` (display order). Stray images (payment icons...) ->
   `fileCreate(files:[{originalSource, contentType: IMAGE}])`.
4. **Trap "Unavailable"**: new products may be published only to a sales channel such as Copilot/Shop/AI channels.
   Confirm with the user, then `productUpdate status: ACTIVE` **and**
   `publishablePublish(id, input:{publicationId: <online_store_publication_gid>})`.
5. If the store runs a store-wide quantity discount (e.g. on a smart collection), exclude this product
   (`volume_discount_exclusion_tag`) or it overrides your tiers.
6. `productUpdate(product:{id, templateSuffix:"ppc-<slug>"})` - only AFTER the theme has the template (stage 5).
7. Option values on Shopify must match the copied swatch `input value` text EXACTLY (including emoji).

## Stage 2 - Extract the reference page

```
py -3 scripts/extract_page.py <reference-url> <work-dir> [gallery-selector] [buybox-selector]
```
- Runs at phone width 390, scrolls the whole page for lazy images. **Reference cart must be EMPTY** (else "Buy 2"
  buttons are captured in their "added" state and do nothing).
- Default selectors: `#product-gallery-wrap` / `#product-form-wrap` (Chinese platforms). Shopify:
  `.product__media-wrapper` / `.product__info-wrapper` (verify in DevTools).
- CSS is filtered to rules matching real elements inside the two blocks (~1 MB -> ~90 KB).
- Rich-content web components with a shadow root (`ws-rich-content`) are opened automatically.
- `meta.json` `skip` lists CORS-blocked stylesheets; if non-empty, download those with curl and inspect by hand.

## Stage 3 - Images + fonts

- Images: on your CDN since stage 1. `build_section.py` reports images still pointing at the reference - must be 0
  (hotlinked images can be blocked or swapped at any time).
- Fonts: `build_section.py` downloads the reference fonts to `out/fonts/`. Upload only fonts actually used (icon font
  + main text font) to Shopify Files: `stagedUploadsCreate(input:[{filename, mimeType:"font/woff2", resource:FILE,
  httpMethod:POST}])` -> save the result JSON -> `py -3 scripts/staged_upload.py <result.json> <out/fonts>` ->
  `fileCreate(files:[{originalSource: <resourceUrl>, contentType: FILE, filename}])` -> put URLs in `font_urls`.
  Shopify CDN sends `Access-Control-Allow-Origin: *`; most reference stores do not (CORS-blocked fonts = icon boxes).
  Check the font licence; if unsure, substitute a free font with similar metrics.
- **`@font-face` inside a shadow root is ignored by browsers** -> fonts live in `assets/ppc-<slug>-fonts.css` in the
  main document, loaded non-blocking (`media="print" onload`).
- **Never inline base64 fonts** in the main CSS (one case: 101 KB base64 -> 1-2 s blank page).

## Stage 4 - Build the section

```
py -3 scripts/build_section.py <work-dir>                       # reads clone-config.json (+ store.json)
py -3 scripts/screenshot.py file:///<work-dir>/out/test.html <work-dir> rebuild
py -3 scripts/screenshot.py <reference-url> <work-dir> reference   # compare side by side, 390 and 1440
```
How it is assembled (proven - do not change without a reason logged in LEARNINGS):
- Content + CSS embedded inline in `<template id="ppc-tpl">`; `templates/clone-runtime.js` attaches it to the
  **Shadow DOM** of `#ppc-root`. No JSON fetch (fetching = 1-2 s blank). Theme CSS cannot hit the rebuild; rebuild CSS
  cannot leak into the theme header/footer.
- Selectors `html`->`.ppc-html`, `body`->`.ppc-body`, `:root`->`.ppc-html`; `rem`->`px` using the reference root size
  (rem inside a shadow root still resolves against the THEME's `<html>`).
- Gallery: their swiper/JS replaced by a `scroll-snap` track + "1 / N" counter + thumbnails; first image preloaded
  with `fetchpriority=high`.
- `html_fixes`: ordered regex rules on the buy box (remove their express-pay buttons, add `data-ppc="buynow"`, slots,
  guardrail removals). Check the printed match count of every rule - 0 means it did nothing.
- `wrappers`: their outer divs so descendant selectors still match.
- Output is split into snippets <= 19 KB (`-c` CSS, `-h` HTML, `-j` runtime JS), each wrapped in `{% raw %}`; the
  section only `{% render %}`s them. Unused `@keyframes` are dropped (one case: 88 KB -> 31 KB).
- Pre-upload warnings: CJK text, text-style emoji without FE0F, reference images, reference name/domain, badge/
  scarcity keywords. Resolve them all.

### Shopify-source pages (Dawn-like themes): 3 CSS fixes, add up front
Put these at the start of the `^` rule in `html_fixes` (see `clone-config.example.json`):
```css
.ppc-body>*,.product>.grid__item{min-width:0}.ppc-body>.page-width{width:100%;box-sizing:border-box}
.product-form__quantity-and-btn{flex-wrap:wrap}.ppc-mx-w{flex:0 0 100%;width:100%}
.product__info-container>*{margin-top:calc(var(--margin-top,0px)*.625);margin-bottom:calc(var(--margin-bottom,0px)*.625)}
.rating-stars .rating-stars-and-text{font-size:16px!important;flex-wrap:nowrap}.rating-stars__label{white-space:nowrap;font-size:14px}
@media (max-width:749px){.product__title h1{font-size:22px!important;line-height:1.3!important}}
```
(1) `.ppc-body` is a grid and `.page-width{margin:0 auto}` -> blocks shrink to min-content of the thumbnail row ->
page 742px wide on a 390 screen. (2) ATC sits in `.product-form__quantity-and-btn` (flex row) -> the inserted mix box
is squeezed sideways. (3) `rem` inside inline `style=""` is NOT converted by the build -> resolves against your
theme's 16px root instead of their 10px -> spacing and star rows 1.6x too big (`.625` = 10/16; adjust for other roots).
Drop the rating rules if the rating widget was removed under the guardrails.

Other Shopify-source rules: remove `<quantity-breaks>`, `<kaching-bundle>`, `pickup-availability`; KEEP `<sticky-atc>`
(stage 7); `payment-button` + installments form -> `<slot>` + `shop_pay: true`; ATC -> `id="ppc-atc" type="button"
class="product_single_add_button ..."`; Buy It Now -> `data-ppc="buynow"`; swatches `.color-swatch` -> add `labelItem`,
their container -> add `variant_select`, drop `checked`; "Style - X" label -> `data-ppc-label="0"
data-label-prefix="Style - "`.

## Stage 5 - Theme

1. Count themes first. **Trap: stores are limited to 20 themes - when full, `themeDuplicate` returns
   `newTheme: null` with NO error.** Ask the user to delete an old one, or overwrite an old draft that is identical
   except for the files you change.
2. `themeDuplicate(id: <MAIN id>, name: "<theme_name_prefix> <Product> v<N> <change>")`; wait until
   `processing == false` (1-2 min; poll, do not block-sleep).
3. Upload with `themeFilesUpsert(themeId, files:[{filename, body:{type: TEXT, value}}])`:
   - **TEXT only.** Body type URL is dead in practice: it reported success three times while the file never
     changed. Each file <= ~19 KB so it passes through a tool call intact. To get a file as a JSON string:
     `py -3 -c "import json,sys;print(json.dumps(open(sys.argv[1],encoding='utf-8').read()))" <file>`.
   - Order: snippets -> sections -> template JSON (a template referencing a missing section is rejected).
   - Shared files (once per theme): `sections/ppc-cart-drawer.liquid` (templates/cart-drawer.liquid, ~29 KB - still
     uploads as one TEXT call), `sections/ppc-related.liquid`, optional `sections/ppc-exit-popup.liquid`,
     `snippets/ppc-announcement-bar.liquid` (+ one `{% render %}` line in `layout/theme.liquid` before the header).
   - Per clone: `sections/ppc-<slug>.liquid`, `snippets/ppc-<slug>-*.liquid`, `assets/ppc-<slug>-fonts.css`,
     `templates/product.ppc-<slug>.json`.
4. **Verify every upload**: `theme(id) { files(filenames:[...]) { nodes { filename size checksumMd5 } } }` and compare
   with `out/manifest.txt` (LF-normalised md5). Mismatch -> re-upload. Note: Python on Windows writes CRLF unless
   `newline="\n"` (the scripts do this); Shopify may also normalise some characters (e.g. an em dash) - if the
   size differs by a few bytes, diff the content before re-uploading.
5. Fastest path for later clones: duplicate a theme that ALREADY has the shared sections, then upsert only the
   small per-clone files.
6. Preview: `https://<public_domain>/products/<handle>?preview_theme_id=<numeric id>`. Every time the user publishes,
   the next change starts from a fresh duplicate of the new MAIN.

## Stage 6 - Quantity discounts (confirm with the user first - live immediately)

One automatic discount per tier, scoped to the product, NOT combining with each other (Shopify applies the best):
```graphql
mutation D($d: DiscountAutomaticBasicInput!) { discountAutomaticBasicCreate(automaticBasicDiscount: $d) {
  automaticDiscountNode { id } userErrors { field message } } }
# $d: {"title":"Buy 2 save 5%","startsAt":"<today>T00:00:00Z",
#      "minimumRequirement":{"quantity":{"greaterThanOrEqualToQuantity":"2"}},
#      "customerGets":{"value":{"percentage":0.05},"items":{"products":{"productsToAdd":["<product gid>"]}}},
#      "combinesWith":{"productDiscounts":false,"orderDiscounts":false,"shippingDiscounts":true}}
```
- Shopify rounds the discount per unit DOWN to the cent -> totals may differ from the reference by 1-2 cents. Accept
  and tell the user. The cart drawer predicts with the same formula.
- Tiers count the total quantity across all variants -> mix & match needs no extra discount setup.
- The tier percentages in `mix.tiers` / drawer `tiers` and the announcement bar text must equal YOUR real discounts.

## Stage 7 - Cart drawer (`templates/cart-drawer.liquid` -> `sections/ppc-cart-drawer.liquid`)

Shared section, placed after `main` in the product template; per-product settings in the template JSON
(`insurance_handle`, `insurance_percent`, `tiers`, texts, accent). Already built - do not rebuild:
- **Renders immediately from local data** (predicts tier prices), server sync runs in the background through a
  queue. Waiting for the server + dimming the drawer was rejected as "broken, laggy".
- Never re-`innerHTML` the whole drawer per click (images flicker); fixed Liquid image URL per variant (the
  `/cart.js` image URL differs -> reload).
- Opens with 2 `requestAnimationFrame` ticks (first open still slides), locks page scroll, Esc closes.
- Intercepts ADD TO CART / "Buy N" / BUY IT NOW / sticky-bar buttons in the **capture phase on the shadow root**.
- Adds via `/cart/add.js` with RELATIVE quantities (no lost items if the initial cart fetch is slow); quantity changes
  via `/cart/update.js` (product + insurance in one call).
- **Merges duplicate ids before `/cart/add.js`**: duplicate item ids make Shopify skip `product_added_to_cart`, so the
  Meta pixel loses AddToCart while the cart looks fine.
- Phone (<750px): full screen; desktop: 400px right panel. Footer: Subtotal/Discount only when discounted, insurance
  row, Total.
- `[hidden]` can be overridden by copied `display:inline-block` rules -> `[hidden]{display:none!important}`.
- **Sticky add-to-cart bar: if the reference has its own, KEEP IT** - in `html_fixes` tag `<sticky-atc>` with
  `data-ppc="sticky"` and its button `data-ppc="sticky-atc"` (put this rule BEFORE the buynow rule: same
  `SectionAtcBtn` id). The runtime shows it after scrolling past the buy button (`data-after-scroll`), rebuilds its
  `<select>` from REAL variants, syncs image/price; its button adds 1 of the selected variant. The drawer's generic bar
  appears ONLY when the reference has no bar of its own.
- **Trap: some themes scroll inside a wrapper element on desktop, not the window** -> listen to `scroll` on
  `document` in the capture phase, never only on `window`.
- No fabricated social proof (no "recently purchased" popups, no "low stock" badges) - see guardrails.

### Mix & match (multi-style products)
Reference stores usually force "pick style -> add -> repeat"; buying 3 different styles is painful. Proven design:
- **A (product page)**: KEEP their style/size buttons (customers need them to browse); hide only their quantity box +
  old tier block; insert a tier list (Buy 1 / 2 -5% / 3 -10% "MOST POPULAR" / 4 -20% "BEST VALUE"), each tier with
  N style pickers + thumbnails, default the middle tier; one ADD TO CART adds all styles. Clicking a style button puts
  it into slot #1 of the active tier (swapping with any slot that already had it - no accidental duplicates).
- A "bundle" variant (price > 2x the cheapest, e.g. "5 pcs") is hidden from the style buttons and sold as its own
  tier ("Buy 5 - Save X%", ask the user for X) with its own automatic discount.
- **C (cart drawer)**: "Add another style - save X% with N more" + a strip of style cards with "+ ADD"; styles in the
  cart show "check xN".
- Enable via `clone-config.json` `"mix": {"tiers": [[1,0,""],[2,5,""],[3,10,"MOST POPULAR"],[4,20,"BEST VALUE"]], "default_tier": 2}`.
- Offer a clickable HTML mockup right after the first rebuild (open it locally for the user) - decisions are faster
  on a mockup than on a description. Do not wait for the user to ask.

### Announcement bar (`templates/announcement-bar-snippet.liquid`)
Theme announcement bars often promise things that are false for this product (e.g. "free shipping on everything").
The snippet shows a rotating bar only on `ppc-*` templates; text from product metafield `ppc.announcement` (lines
separated by `|`), optional `ppc.announcement_bg` / `_fg`. Write it from YOUR real tiers and threshold.
Trap: themes with `body{display:flex;flex-direction:column}` squeeze the bar to 0px unless `flex:0 0 auto`.

### Real Shop Pay + installments
The reference's "Buy with Shop" button and "Pay in N installments" line belong to THEIR store - copied HTML does
nothing. If your store has Shop Pay (`shop.paymentSettings.supportedDigitalWallets` contains `SHOPIFY_PAY`), set
`"shop_pay": true`: the build places `{{ form | payment_button }}` and `{{ form | payment_terms }}` in the LIGHT DOM of
`#ppc-root` (Shopify's scripts cannot reach a shadow root) and they render in place via `<slot name="ppc-pay">` /
`<slot name="ppc-terms">` (add those with `html_fixes`). The runtime keeps their `input[name=id]` on the selected
variant. Shop Pay buys 1 of the selected variant immediately (skips drawer and mix tiers).

### Delivery dates
"Order now, arrives Mar 3rd - Mar 8th" blocks in the style of dynamic-date apps (`data-dynamic-date="true"`,
`data-text` with `[start_date]`/`[end_date]`, `data-min-days`/`data-max-days`) are recomputed by the runtime for the
viewer's date. Set the day ranges to YOUR real fulfilment + transit times.

### Related products (`templates/related-products.liquid` -> `sections/ppc-related.liquid`)
"You May Also Like" grid (4 columns desktop / 2 phone) from product metafield `ppc.related`
(`list.product_reference`); empty -> hidden. Change the list without touching the theme:
```graphql
mutation { metafieldsSet(metafields:[{ownerId:"<product gid>", namespace:"ppc", key:"related",
  type:"list.product_reference", value:"[\"gid://shopify/Product/<id>\"]"}]) { userErrors { message } } }
```
Ask the user which products to link (sensible default: other ACTIVE products with `<product_tag>`).

### Exit-intent popup, optional (`templates/exit-popup.liquid` -> `sections/ppc-exit-popup.liquid`)
Email -> code revealed immediately and auto-applied (`/discount/<CODE>`). Renders nothing without `brand` and `code`
(no defaults). ESP-agnostic: dispatches `document` event `ppc:lead {email, code, source}`; Klaviyo client
subscriptions built in when `klaviyo_public_key` + list are set (public id, not a secret).
- Create FIRST (with the user's confirmation): the discount code (`discountCodeBasicCreate`, product-scoped,
  once per customer, combines with shipping only), the list, and the automation that emails the code.
- Measured behaviour: the code does NOT stack with tier discounts; Shopify applies whichever is better for the
  customer. No tier change needed. Match the percent to any site-wide popup the store already runs (two different
  offers confuse shoppers).
- Triggers: desktop mouse leaving the top edge; phone scrolled > 1200px then a fast swipe up. Not in the first 8 s,
  once per session, not for visitors already identified by the ESP (so it may not show in the user's own browser).
- `hide_group`: hides a single-value variant group in the Shadow DOM. Never delete the option on Shopify instead (it
  breaks variant matching).
- Background/hidden automation tabs cannot test swipes - ask the user to try on a real phone.

## Stage 8 - Shipping (per-product delivery profile - confirm first, live immediately)

```graphql
mutation P($p: DeliveryProfileInput!) { deliveryProfileCreate(profile: $p) { profile { id } userErrors { field message } } }
# $p: {"name":"PPC <slug> shipping","variantsToAssociate":["<variant gid>", ...],
#  "locationGroupsToCreate":[{"locations":["<location_gid>"],"zonesToCreate":[{"name":"United States",
#   "countries":[{"code":"US","includeAllProvinces":true}],"methodDefinitionsToCreate":[
#    {"name":"Standard Shipping","rateDefinition":{"price":{"amount":"6.99","currencyCode":"USD"}},
#     "priceConditionsToCreate":[{"criteria":{"amount":"59.98","currencyCode":"USD"},"operator":"LESS_THAN_OR_EQUAL_TO"}]},
#    {"name":"Free Shipping","rateDefinition":{"price":{"amount":"0","currencyCode":"USD"}},
#     "priceConditionsToCreate":[{"criteria":{"amount":"59.99","currencyCode":"USD"},"operator":"GREATER_THAN_OR_EQUAL_TO"}]},
#    {"name":"Expedited Shipping","rateDefinition":{"price":{"amount":"12.99","currencyCode":"USD"}}}]}]}]}
```
- Price conditions apply to the cart **after discounts**.
- **A profile with only a US zone means customers in other countries can no longer buy this product** (the general
  profile may have had international zones). Warn the user; add zones if they sell abroad.
- Live immediately, no theme publish needed. Do not edit the general profile.
- Use the user's real rates and thresholds; the reference's are only a starting suggestion.
- Verify on a test cart: `POST /cart/prepare_shipping_rates.json?shipping_address[country]=United%20States&shipping_address[province]=<state>&shipping_address[zip]=<zip>`
  then `GET /cart/async_shipping_rates.json?...` (repeat until `shipping_rates` appears).
- Check `shop.shopPolicies` (shipping policy) does not contradict the product's rates.

## Stage 9 - Shipping insurance (optional - confirm first)

Non-Plus Shopify cannot add a checkbox to checkout. Pattern:
- A hidden product "Shipping Insurance", handle in `store.json` `insurance_product_handle`; one variant per price point
  (option "Amount"), price = round(`insurance_percent` x item price), e.g. 5% x 32.99 = 1.65.
  `productCreate` + metafield `seo.hidden = 1` + exclusion tag -> `productVariantsBulkUpdate` (`taxable:false`,
  `inventoryPolicy:CONTINUE`, `inventoryItem:{requiresShipping:false, tracked:false}`) -> `publishablePublish` Online
  Store. Make sure it is in no collection.
- New product with a different price -> `productVariantsBulkCreate` a new price point; no code change (the drawer picks
  the variant whose price = round(% x variant price), one insurance line per product line).
- The tick box lives in the cart drawer; insurance quantity follows product quantity (self-heals). In checkout it is
  a normal line item.
- Pre-ticked insurance increases complaints/chargebacks and is restricted in some jurisdictions - tell the user;
  recommend unticked by default unless they decide otherwise. Write insurance texts truthfully (what it covers).

## Stage 10 - Acceptance (mandatory, with numbers)

Run every check in `CHECKS.md` on `?preview_theme_id=` and record the measured values in your report. Compare drawer
numbers with `/cart.js` AFTER the server answers. Read checkout totals, never fill or pay. Clear test carts.
Hidden automation tabs freeze `requestAnimationFrame` and transitions (screenshots hang): numbers can still be read
via JS, but "smoothness" must be confirmed by the user looking at it.

Sharing preview: the product page has `og:image` from the featured image (Shopify CDN serves JPEG to crawlers even for
.webp). Links shared before going live keep a stale preview -> the user re-scrapes in the Facebook Sharing Debugger.

---

## Silent traps (each one cost real time)

| Trap | Symptom | Avoid |
|---|---|---|
| `themeDuplicate` with 20 themes | `newTheme: null`, no error | count themes first; ask user to delete one |
| `themeFilesUpsert` body type URL | "success", file unchanged | TEXT only, snippets <= 19 KB, verify md5 |
| md5 mismatch from CRLF | checksum differs, content same | write LF (`newline="\n"`), normalise before md5 |
| Extracting while reference cart has items | "Buy 2" captured as "added" div, does nothing | extract with empty cart; fix to `<button class="addToCart">` |
| Multi-variant product | `.labelItem` does not change price, wrong variant added | variants JSON + runtime; option values must match their `input value` exactly (incl. emoji) |
| Writing to MAIN theme | API refuses / live store breaks | always duplicate; re-duplicate after each publish |
| Product only on a non-Online-Store channel | page says "Unavailable" | ACTIVE + publishablePublish Online Store |
| Store-wide quantity discount | overrides clone tiers | exclusion tag |
| `@font-face` in shadow root | icons render as boxes | fonts in main-document asset |
| Base64 fonts / fetched content | 1-2 s blank page | inline content, rehosted fonts, preload first image |
| Drawer waits for server | "broken, laggy" | render first, sync in background |
| `[hidden]` overridden | elements never hide | `[hidden]{display:none!important}` |
| Per-product delivery profile | foreign customers cannot buy | warn / add zones |
| Duplicate ids in `/cart/add.js` | no Meta AddToCart event | merge items by id |
| `rem` in inline `style=""` | spacing/stars 1.6x on Shopify sources | the 3 CSS fixes |
| Dawn grid min-content | page wider than screen | `min-width:0`, `width:100%` |
| ATC in flex row container | mix box squeezed | `flex-wrap:wrap`, mix `flex:0 0 100%` |
| Theme scrolls in a wrapper | sticky bar never appears on desktop | document scroll listener, capture phase |
| Text emoji without FE0F | phones draw a box that looks like CJK text | runtime appends FE0F; check at 390px |
| Sharing an automation Chrome | other jobs silently degrade | dedicated CDP Chrome, close your tabs |
| Preview vs publish | user sees old page on the live URL | preview link until the user publishes |
| Changing option values before publishing new runtime | variant buttons stop matching | publish the theme with the new runtime FIRST |

Third-party page-builder / store-cloning SaaS tools tend to "re-create" rather than copy, and some only read Shopify
sources. If the user asks about them, check they work today before recommending; this skill does not depend on them.

---

## Make this skill better after every run (mandatory)

This skill is a living document. Every run and every correction must leave a trace, or the next run repeats the
mistake.

**Before starting**: read `LEARNINGS.md`, `CASES.md`, `CHECKS.md` (see top of this file).

**After every run** (and immediately whenever the user corrects something):
1. **LEARNINGS.md** - append a row: date · what the user saw / pointed out · real root cause · rule. A mistake already
   in LEARNINGS that happens again = the skill is broken: fix the skill before fixing the page.
2. **CASES.md** - new situation (platform, variant shape, offer type, theme quirk) -> add a row "situation -> what to
   do differently", with the working solution.
3. **CHECKS.md** - anything that broke and a machine can verify -> add a numbered check "action -> must see". A trap
   that bit 2+ different runs -> also add it to "Silent traps" above.
4. **SKILL.md / scripts / templates** - when a rule is general, propose the edit to the user in one line and make it
   in the same run (do not leave it for "later").
5. **Run log** - append to the Run log in `LEARNINGS.md`: date, branch (CASES row), minutes to first preview, minutes
   total, number of user correction rounds, which correction a check could have caught. Use it to estimate the next run.
6. **Keep the shared files generic**: store names, domains, IDs, prices, product names go ONLY in `store.json` or
   local notes - never in SKILL.md / LEARNINGS / CASES / CHECKS.
7. **Re-verify old facts**: platform APIs, tool limits and reference-site markup change. A fact older than a few weeks
   that a decision depends on -> test it again before trusting it.
8. **Decisions belong to the user** (prices, percents, keep/drop a block): build a clickable mockup, do not choose.
9. Improvements that would help other users -> suggest sending them upstream as a pull request (generic wording,
   no store data).
