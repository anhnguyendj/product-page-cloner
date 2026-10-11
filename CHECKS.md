# CHECKS

Acceptance checks. Run ALL of them on the preview (`?preview_theme_id=`), in the dedicated CDP Chrome or the agent's
browser, and report the measured values. Every row exists because it broke once. Add a row whenever something breaks
that a machine can verify. Never fill checkout forms or pay; clear the test cart at the end.

| # | Action | Must see |
|---|---|---|
| K1 | click ADD TO CART | drawer opens immediately (< 50 ms); numbers match `/cart.js` after the server answers |
| K2 | go 1 -> 2 -> 3 -> 4 (-> 5) items | tip line + Subtotal / Discount / Total match `/cart.js`; tip text matches the measured reference behaviour with YOUR percents |
| K3 | untick insurance, tick again | insurance line disappears + warning shows; comes back with the right quantity |
| K4 | `prepare_shipping_rates` below / above the free-shipping threshold | exactly the rates and names of the stage 8 table |
| K5 | scan rendered page + every shadow root + drawer (text, `alt`, `title`, `placeholder`, `aria-label`, `value`) and product title/options/description for CJK `[⺀-鿿豈-﫿＀-￯　-〿]` and text emoji without FE0F | 0 hits |
| K6 | widths 360 / 375 / 390 / 414 | style buttons <= 2 lines; drawer width == `innerWidth` |
| K7 | mix: click one style, ADD TO CART on tier 3 | 3 different styles added, no unintended duplicates |
| K8 | open an OLDER cloned product on the new theme | still works (shared drawer) |
| K9 | bottom of page | "You May Also Like" has images, correct links, correct prices |
| K10 | capture network (CDP `Target.setAutoAttach` + `Network.enable`, incl. iframes) while viewing + clicking ADD TO CART | pixel events PageView, ViewContent and **AddToCart** fire (e.g. Meta `facebook.com/tr`) |
| K11 | read `shop.shopPolicies` shipping policy + announcement text | no contradiction with this product's real rates and tiers |
| K12 | inside the shadow root at 390px: `document.documentElement.scrollWidth`, `h1` font-size, rating row | scrollWidth == 390 · h1 <= 22px · rating row one line (if a rating row is legitimately present) |
| K13 | scroll past the buy button at 390 and 1440; compare with the reference's sticky bar; click its button | looks like theirs; generic bar `.sb` NOT shown; cart +1 of the selected variant |
| K14 | price area + below BUY IT NOW | "Pay in N installments" line + Shop Pay button render when the reference had them and `shop_pay` is on |
| K15 | upload verification | every theme file's `size` / `checksumMd5` equals `out/manifest.txt` |
| K16 | first paint | no blank flash; images, fonts and icons all present (compare `screenshot.py` reference vs rebuild at 390 and 1440) |
| K17 | REMOVE every line; BUY IT NOW | empty cart state; BUY IT NOW lands on `/checkout` (stop there) |
| K18 | guardrail scan of visible HTML | 0 occurrences of the reference store name/domain, third-party rating badges, fabricated counts, fake origin claims, fake scarcity |
| K19 | product status + publications | ACTIVE and published to Online Store; template suffix `ppc-<slug>`; no "Unavailable" on the page |
| K21 | real-data social proof: compare `ppc.recent_orders` with the latest paid orders; set a tracked variant to qty <= `low_stock_max`, then an untracked one | every notice = a real order (time matches `createdAt`, name masked to initial + `***`); low-stock line only on the tracked variant, with its real quantity |
| K22 | LITE block pasted: phone width screenshot; pick tier 3, ADD TO CART | looks like the reference; cart has 3 of the product; cart/checkout discount equals the tier shown |
| K20 | cleanup | test carts cleared on your store; reference cart restored; tabs you opened are closed |
