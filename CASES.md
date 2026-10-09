# CASES

Decision table. Read at stage 0 to find which branch this clone belongs to; add a row for every new situation.
Generic wording only - no store names or IDs.

| Situation | What to do differently |
|---|---|
| Reference on a Chinese storefront platform (class names like `data-v-...`, Vue app) | default selectors `#product-gallery-wrap` / `#product-form-wrap`; wrappers = their `#app ... .container` chain; replace their quick-pay block with `data-ppc="buynow"` |
| Reference is Shopify (Dawn-like theme) | selectors `.product__media-wrapper` / `.product__info-wrapper`; add the 3 Shopify CSS fixes to the `^` rule; remove `<quantity-breaks>`, `<kaching-bundle>`, `pickup-availability`; KEEP `<sticky-atc>`; payment button + installments -> `<slot>` + `shop_pay: true`; ATC -> `id="ppc-atc" type="button" class="product_single_add_button ..."`; Buy It Now -> `data-ppc="buynow"`; `.color-swatch` -> add `labelItem`, container -> `variant_select`, drop `checked` |
| Reference root font-size is not 10px | change the `.625` factor to reference_root / your_theme_root |
| Single-variant product | no `mix`; drawer tiers from the `tiers` setting |
| Multi-style product, same price | `mix` (A+C); Shopify option values must match their `input value` text exactly (incl. emoji) |
| A "bundle" variant (price > 2x the cheapest) | hidden from style buttons; becomes a tier "Buy N - Save X%" with its own automatic discount; user chooses X |
| Variant group with a single value | `hide_group` in the exit popup section or html_fixes; never delete the option on Shopify |
| Insurance price differs from existing price points | add a variant to the insurance product; no code change |
| Different free-shipping threshold | own delivery profile + announcement metafield with YOUR threshold |
| Other clones already live on the store | link them via `ppc.related` (ask the user) |
| User's tiers differ from the reference's | `mix.tiers`, drawer `tiers`, discounts and announcement text all use the USER's numbers, never the reference's text |
| Reference shows third-party rating badges, review counts, "designed in <city>", fake stock/countdown/"recently purchased" | remove with html_fixes; tell the user why; do not re-ask after they accept |
| Reference images/copy are the only media available | ask the user: use their own media (recommended) or accept the copyright risk themselves; record the decision |
| Reference has its own sticky add-to-cart bar | keep it (`data-ppc="sticky"`, button `data-ppc="sticky-atc"`, rule before buynow) |
| Reference has no sticky bar | drawer's generic bar appears automatically |
| Reference has delivery-date blocks | runtime recomputes; set day ranges to YOUR fulfilment + transit times |
| Theme scrolls in a wrapper on desktop | already handled (document capture listeners); verify with CHECKS K13 at 1440 |
| Store already runs a store-wide quantity discount | exclude the product (tag) so it does not override the clone tiers |
| Store has 20 themes | ask the user to delete one, or overwrite an identical old draft |
| Store sells internationally | add zones to the per-product delivery profile |
| Store already runs a site-wide email popup | match its percent in the exit popup, or skip the exit popup |
