# Connect your agent to your Shopify store

This skill needs an agent that can run **Shopify Admin GraphQL queries and mutations** on *your* store
(themes, theme files, products, files, discounts, shipping, metafields, publications).
Pick ONE of the three paths below, then run the [connection check](#connection-check).

> Sources read on 2026-10-09 (Shopify Help Center, shopify.dev, code.claude.com, OpenAI Codex docs).
> Shopify changes this area often. If a step no longer matches what you see, follow the official page linked
> in that step, then open an issue or PR here so the next person doesn't get stuck.

| Your agent | Recommended path |
|---|---|
| Claude Code / Claude desktop / claude.ai | **A. Shopify connector for Claude** (tested end-to-end with this skill) |
| OpenAI Codex CLI, Cursor, VS Code agents, Claude Code without a claude.ai login | **B. Shopify CLI** (official connector for local AI tools) |
| Anything else, or B is blocked | **C. Direct Admin GraphQL** with `scripts/admin_graphql.py` |

`@shopify/dev-mcp` (Shopify Dev MCP) is useful **in addition** (docs + GraphQL schema lookups) but it has **no
access to your store**. It cannot replace A, B or C.

---

## Scopes this skill uses

| Scope | Used for |
|---|---|
| `read_themes`, `write_themes` | `themes`, `themeDuplicate`, `themeFilesUpsert`, reading theme files |
| `read_products`, `write_products` | create/update the product, variants, `templateSuffix`, product metafields |
| `read_files`, `write_files` | `stagedUploadsCreate` + `fileCreate` (fonts, extra images) |
| `read_discounts`, `write_discounts` | `discountAutomaticBasicCreate` (quantity tiers), optional popup code |
| `read_shipping`, `write_shipping` | `deliveryProfileCreate` (per-product shipping) |
| `read_publications`, `write_publications` | `publishablePublish` to the Online Store channel |
| `read_locations` | find your location ID for the delivery profile |

Grant only these. The skill never needs orders, customers, payments or refunds.

**Theme writes:** Shopify documents `themeFilesUpsert` / `themeDuplicate` as needing `write_themes` *and* an
exemption for **public** apps. Store-owner connections (path A tested; B and C should behave the same, verify with the
connection check) can write to **unpublished** themes. Nobody's connection should write to your live theme: this skill
always duplicates the live theme, edits the copy, and you publish it yourself.

---

## A. Claude: the Shopify connector (tested)

1. In claude.ai open **Settings → Connectors** (directory: `claude.ai/directory/connectors/shopify`) and add **Shopify**.
   You are sent to your Shopify admin to approve access. Official guide:
   <https://help.shopify.com/en/manual/ai-powered-tools/connecting-ai-tools/shopify-connector-for-claude>
2. Claude Code: log in with the same claude.ai account (`claude` → `/login`). Connectors you added on claude.ai show up
   automatically; run `/mcp` and check that the Shopify server is **connected**
   (<https://code.claude.com/docs/en/mcp>).
3. The connector exposes `graphql_query` and `graphql_mutation` (plus product/order helpers). By Shopify's design it
   **can edit an unpublished theme but cannot edit the live theme, publish a theme, or delete one**. That matches this
   skill's workflow.
4. Your staff permissions limit what it can do. Use an owner or staff account with Themes, Products, Discounts and
   Shipping permissions.

Tested with this skill (2026-10): `themeDuplicate`, `themeFilesUpsert` (TEXT bodies, unpublished theme),
`stagedUploadsCreate`, `fileCreate`, `productCreate/Update`, `publishablePublish`, `discountAutomaticBasicCreate`,
`deliveryProfileCreate`, `metafieldsSet`.

---

## B. Codex, Cursor, other local agents: Shopify CLI

Shopify's official connector for local AI tools is the Shopify CLI (needs CLI 3.93+):
<https://help.shopify.com/en/manual/ai-powered-tools/shopify-cli-connector>

1. Install Node 20+ and the CLI: `npm install -g @shopify/cli@latest` (check with `shopify version`).
2. Authenticate once per store with the scopes above (a browser window opens for approval):

   ```bash
   shopify store auth --store YOUR-STORE.myshopify.com \
     --scopes read_themes,write_themes,read_products,write_products,read_files,write_files,read_discounts,write_discounts,read_shipping,write_shipping,read_publications,write_publications,read_locations
   ```
   Docs: <https://shopify.dev/docs/api/shopify-cli/store/store-auth>
3. The agent runs GraphQL through the CLI. Mutations are off unless you pass `--allow-mutations`:

   ```bash
   shopify store execute -s YOUR-STORE.myshopify.com --query-file q.graphql --json
   shopify store execute -s YOUR-STORE.myshopify.com --query-file m.graphql -v '{"id":"gid://..."}' --allow-mutations --json
   ```
   Docs: <https://shopify.dev/docs/api/shopify-cli/store/store-execute>
4. Optional but helpful, the Shopify AI Toolkit (teaches the agent the CLI and API):
   - Codex: `codex plugin add shopify@openai-curated`
   - Claude Code: `claude plugin install shopify-ai-toolkit@claude-plugins-official`

   (<https://shopify.dev/docs/apps/build/ai-toolkit>)
5. Optional docs/schema MCP (no store access):
   - Codex: `codex mcp add shopify-dev -- npx -y @shopify/dev-mcp@latest` (or in `~/.codex/config.toml`:
     `[mcp_servers.shopify-dev]` / `command = "npx"` / `args = ["-y", "@shopify/dev-mcp@latest"]`)
   - Claude Code: `claude mcp add --transport stdio shopify-dev -- npx -y @shopify/dev-mcp@latest`
   - Cursor: `.cursor/mcp.json` → `{"mcpServers":{"shopify-dev":{"command":"npx","args":["-y","@shopify/dev-mcp@latest"]}}}`

Tell your agent at the start: *"Use `shopify store execute` for every Shopify Admin GraphQL call in this skill; pass
`--allow-mutations` only for mutations."*

---

## C. Direct Admin GraphQL (any agent that can run a shell)

Use this if your agent can't use A or B. Since 2026-01-01 new custom apps are created in the **Dev Dashboard**
(the old "Develop apps" custom apps can no longer be created):
<https://shopify.dev/docs/apps/build/dev-dashboard/create-apps-using-dev-dashboard>

1. Dev Dashboard → **Create app** → create a **version** with the scopes above → **install** it on your store.
2. App settings → copy **Client ID** and **Client secret**. The app and the store must belong to the same Shopify
   organization.
3. Put them in environment variables (or a `.env` that is in `.gitignore`, never committed, never pasted in chat):

   ```
   SHOPIFY_STORE=your-store.myshopify.com
   SHOPIFY_CLIENT_ID=
   SHOPIFY_CLIENT_SECRET=
   ```
4. `scripts/admin_graphql.py` exchanges them for a 24-hour token (client credentials grant,
   <https://shopify.dev/docs/apps/build/authentication-authorization/access-tokens/client-credentials-grant>) and calls
   `https://{store}/admin/api/2026-10/graphql.json`. It **refuses to write to the live (MAIN) theme** and to publish or
   delete themes:

   ```bash
   py -3 scripts/admin_graphql.py query  '{ shop { name } }'
   py -3 scripts/admin_graphql.py mutate --file m.graphql --vars vars.json
   ```
   If you already have an Admin API access token (older custom app), set `SHOPIFY_ACCESS_TOKEN` instead of the client
   pair.

Community MCP servers exist, but the ones we checked expose fixed tools (products/orders/customers). They do not have
raw GraphQL or theme-file tools, so they can't run this skill on their own.

---

## Connection check

Ask your agent to run these two **read-only** queries before using the skill:

```graphql
{ shop { name myshopifyDomain } }
```
```graphql
{ themes(first: 20) { nodes { id name role processing } } }
```

Pass = your shop name comes back, and you see one theme with `role: MAIN`. Also note how many themes you have:
Shopify allows **20**. At 20, `themeDuplicate` silently returns `null`, so delete an old unpublished theme first.

The first real run then confirms write access. Stage 5 duplicates the live theme and upserts one small file. If that
fails with an access or exemption error, switch to another path above and tell us in an issue.
