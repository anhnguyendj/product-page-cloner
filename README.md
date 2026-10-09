# product-page-cloner

A [Claude Code](https://claude.com/claude-code) skill that rebuilds a reference product page's **layout and buying
UX** on **your own Shopify store**, pixel-faithful, on a duplicated (unpublished) theme that you review and publish.

It copies the rendered structure of two blocks - the gallery and the buy box - instead of "re-designing" them, then
wires them to your real products, variants, discounts, cart and checkout:

- gallery + buy box extracted at 390px with CSS filtered down to the rules actually used
- embedded in a Shadow-DOM section (no CSS collisions with your theme, no blank flash)
- variants / swatches, **mix & match** quantity tiers, bundle tiers
- slide-in **cart drawer** with instant (optimistic) rendering and queued server sync
- automatic quantity discounts, per-product delivery profile, optional shipping-insurance line
- the reference's own sticky add-to-cart bar, your **real Shop Pay** button + installments
- dynamic delivery dates, related products (metafield), optional exit-intent email popup (ESP-agnostic),
  per-product announcement bar
- numbered acceptance checks, md5 upload verification, a long list of silent traps already solved

Works with references on Shopify and on Chinese storefront platforms (Shoplazza-style).

## Requirements

- An AI coding agent: Claude Code, OpenAI Codex CLI, Cursor, or similar
- **Shopify Admin access for that agent** - read **[SETUP.md](SETUP.md)** first. Three ways:
  - A. Claude: the official Shopify connector for Claude (tested with this skill)
  - B. Codex / Cursor / others: Shopify CLI (`shopify store auth` + `shopify store execute --allow-mutations`)
  - C. Any agent with a shell: a Dev Dashboard app + `scripts/admin_graphql.py`
  (Shopify Dev MCP alone is NOT enough - it reads docs, not your store.)
- Python 3 with `pip install websockets` (Pillow optional, for comparing screenshots)
- Google Chrome (a dedicated profile with remote debugging for the scripts; see `scripts/cdp.py`)
- Optional: a browser-automation tool for the agent (e.g. Claude in Chrome) to measure reference pages

## Install

```bash
git clone https://github.com/anhnguyendj/product-page-cloner ~/.claude/skills/product-page-cloner
# Codex: put it where your agent reads skills/instructions (e.g. ~/.codex/skills/) or point the agent at SKILL.md
cd ~/.claude/skills/product-page-cloner
cp store.example.json store.json      # then fill it in (or let the agent discover the IDs)
pip install websockets
```

`store.json` and every `clone-config.json` are gitignored - your store facts never leave your machine.

## Quickstart

1. Start a dedicated Chrome for the scripts (default port 9230):
   `chrome --remote-debugging-port=9230 --user-data-dir=/tmp/ppc-chrome`
2. In Claude Code: *"Make my product page for <my product> look like https://reference.example/products/x"*.
3. The agent follows `SKILL.md` stages 0-10: measures the reference, creates/updates your product, extracts the page,
   builds the section (`scripts/build_section.py`), uploads to a **duplicated** theme, sets up discounts / shipping /
   insurance **after asking you**, runs the acceptance checks and sends you a preview link.
4. You review the preview and publish the theme yourself.

Manual use of the scripts:

```bash
py -3 scripts/extract_page.py <reference-url> work/my-product            # python3 on macOS/Linux
cp clone-config.example.json work/my-product/clone-config.json          # edit it
py -3 scripts/build_section.py work/my-product                          # -> work/my-product/out/
py -3 scripts/screenshot.py file:///.../out/test.html work/my-product rebuild
```

## Guardrails

The skill mirrors layout and UX only. It will:

- never copy the reference store's name, logo, domain or trademarks
- never reproduce third-party rating badges, review counts, fake origin claims, fake countdowns, fake stock counters
  or fake "recently purchased" notifications - and it tells you why it removed them
- default to **your own** product photos and copy; reusing someone else's media is a copyright decision you make and
  are responsible for
- never write to your live theme (duplicate -> preview -> you publish)
- ask before any change that is live immediately (discounts, delivery profiles, product status)
- never place orders or pay while testing checkout, and clear test carts

## How it gets better after every run

The skill keeps its own memory in plain files:

- `LEARNINGS.md` - every mistake a user pointed out, its root cause and the rule that prevents it, plus a run log
  (time to first preview, correction rounds) used to estimate the next run
- `CASES.md` - decision table "situation -> what to do differently" (platform, variant shape, offer type, theme quirks)
- `CHECKS.md` - numbered acceptance checks (action -> must see); each exists because something broke once

The agent reads all three before starting and appends to them after every run and every correction. General rules
are promoted into `SKILL.md`, scripts or templates in the same run. Store-specific facts stay in `store.json`.

## Contributing

Improvements are welcome - especially new rows for `LEARNINGS.md`, `CASES.md` and `CHECKS.md` from real runs.
Open a pull request with generic wording (no store names, domains, IDs, prices or product names), and describe the
situation, the root cause and how you verified the fix. Keep scripts dependency-light and Windows-safe
(explicit UTF-8, LF line endings for files uploaded to Shopify).

## License

MIT - see `LICENSE`.
