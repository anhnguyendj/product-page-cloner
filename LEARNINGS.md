# LEARNINGS

Mistakes a user pointed out (or the agent caught itself) -> real root cause -> rule. Append a row every time.
A mistake that is already here and happens again means the skill is broken: fix SKILL.md / scripts / templates first.
Generic wording only - no store names, domains, IDs or prices (those belong in `store.json` / local notes).

| Date | What the user saw / pointed out | Real root cause | Rule (where it now lives) |
|---|---|---|---|
| YYYY-MM-DD | *example:* cart drawer "broken, lags a few beats" | drawer waited for 2 server round-trips and dimmed itself | render from local data first, sync in background (stage 7) |
| seed | cart tip / tier block missing from drawer | reference cart was never measured | stage 0: measure the cart at 1/2/3/4 items |
| seed | sticky bar and other widgets missing | looked at one viewport only, did not wait | stage 0: measure at 390 and 1440, wait 30 s |
| seed | announcement bar still showed the theme's generic promise | bar belongs to the theme, not the section | per-product metafield `ppc.announcement` |
| seed | hard to buy several different styles | copied the reference's one-style-per-add flow | multi-style product -> offer mix & match mockup right after first rebuild |
| seed | style/size buttons disappeared | mix & match hid their whole variant block | keep their style buttons; hide only qty box + old tier block |
| seed | bundle variant mixed in with single styles | a bundle is not a style | bundle (price > 2x cheapest) = its own tier, hidden from style buttons |
| seed | "there is Chinese text" on phone | text-style emoji without U+FE0F drawn as a box | CJK + emoji scan (CHECKS K5); runtime appends FE0F |
| seed | 5 style buttons wrapped to 3 lines on phone | letter-spacing + 12px padding | phone: 11.5px text, 6px padding -> 2 lines at 360-414 px |
| seed | size on page did not match what the supplier ships | copied the reference text without checking the supplier | stage 0: get real size/weight from the supplier BEFORE building |
| seed | (self-caught) no Meta AddToCart although items were added | `/cart/add.js` items had duplicate ids | merge items by id (drawer `addMany`); CHECKS K10 |
| seed | sticky bar looked different from the reference | html_fixes removed their `<sticky-atc>` and a generic bar was used | keep the reference's own sticky bar (stage 7); CHECKS K13 |
| seed | "they have Buy with Shop, why don't we" | removed their express button without adding ours | `shop_pay: true` + `<slot>`; CHECKS K14 |
| seed | title and review line huge, wrapping on phone | `rem` in inline styles resolved against theme root 16px (reference 10px) | Shopify-source CSS fixes; CHECKS K12 |
| seed | (self-caught) "Buy 2" button dead | extracted while the reference cart had items | extract with an empty reference cart |
| seed | user asked to keep a third-party rating badge / origin claim | those are another store's reviews / a false claim | refuse, remove in html_fixes, explain why (guardrails) |

## Run log

Append one line per run. Used to estimate the next run.

| Date | Branch (CASES row) | Min to first preview | Min total | User correction rounds | Correction a check could have caught |
|---|---|---|---|---|---|
| seed | Chinese platform, 1 variant | ~1 day (first ever run, discovery) | 2 days | 4 | cart measurement, sticky bar |
| seed | Chinese platform, multi-style | ~180 (URL upsert dead, switched to TEXT) | ~6 h | 6 | mix & match mockup, emoji, button wrap |
| seed | Shopify source (Dawn-like) | ~150 | ~4 h | 3 | sticky bar, Shop Pay, rem sizing |
