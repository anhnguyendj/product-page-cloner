"""Minimal Shopify Admin GraphQL client for agents without a Shopify MCP / CLI (SETUP.md path C).

Credentials come from environment variables only (never pass them on the command line, never print them):
  SHOPIFY_STORE          your-store.myshopify.com
  SHOPIFY_ACCESS_TOKEN   an Admin API access token            (option 1)
  SHOPIFY_CLIENT_ID      Dev Dashboard app client id          (option 2: client credentials grant, 24h token)
  SHOPIFY_CLIENT_SECRET  Dev Dashboard app client secret
  SHOPIFY_API_VERSION    optional, default 2026-10

Usage:
  py -3 admin_graphql.py query  '{ shop { name } }'
  py -3 admin_graphql.py query  --file q.graphql [--vars vars.json]
  py -3 admin_graphql.py mutate --file m.graphql [--vars vars.json]

Safety: refuses themePublish / themeDelete, and refuses themeFilesUpsert / themeFilesDelete / themeFilesCopy /
themeUpdate on the live (MAIN) theme. Work on a duplicated theme; the store owner publishes it.
"""
import json, os, re, sys, urllib.request, urllib.error

STORE = os.environ.get("SHOPIFY_STORE", "").strip().replace("https://", "").strip("/")
VERSION = os.environ.get("SHOPIFY_API_VERSION", "2026-10")
BLOCKED = ("themePublish", "themeDelete")
THEME_WRITES = ("themeFilesUpsert", "themeFilesDelete", "themeFilesCopy", "themeUpdate")


def die(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(2)


def post(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json", **headers}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        die(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def token():
    t = os.environ.get("SHOPIFY_ACCESS_TOKEN", "").strip()
    if t:
        return t
    cid, sec = os.environ.get("SHOPIFY_CLIENT_ID", "").strip(), os.environ.get("SHOPIFY_CLIENT_SECRET", "").strip()
    if not (cid and sec):
        die("Set SHOPIFY_ACCESS_TOKEN, or SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET (see SETUP.md, path C).")
    r = post(f"https://{STORE}/admin/oauth/access_token",
             {"grant_type": "client_credentials", "client_id": cid, "client_secret": sec}, {})
    if "access_token" not in r:
        die("Token request failed: " + json.dumps({k: v for k, v in r.items() if k != "access_token"})[:300])
    return r["access_token"]


def gql(tok, query, variables=None):
    return post(f"https://{STORE}/admin/api/{VERSION}/graphql.json",
                {"query": query, "variables": variables or {}}, {"X-Shopify-Access-Token": tok})


def guard(tok, query, variables):
    for name in BLOCKED:
        if re.search(r"\b" + name + r"\s*\(", query):
            die(f"Refused: {name}. Publishing/deleting themes is the store owner's job, in the Shopify admin.")
    if any(re.search(r"\b" + n + r"\s*\(", query) for n in THEME_WRITES):
        ids = set(re.findall(r"gid://shopify/OnlineStoreTheme/\d+", query + json.dumps(variables or {})))
        if not ids:
            die("Refused: theme write without an explicit theme gid in the query or variables.")
        main = gql(tok, "{ themes(first: 50, roles: [MAIN]) { nodes { id } } }")
        main_ids = {n["id"] for n in main.get("data", {}).get("themes", {}).get("nodes", [])}
        if ids & main_ids:
            die("Refused: this would write to the LIVE (MAIN) theme. Duplicate it and write to the copy.")


def main():
    a = sys.argv[1:]
    if not a or a[0] not in ("query", "mutate"):
        die(__doc__)
    if not STORE.endswith(".myshopify.com"):
        die("Set SHOPIFY_STORE=your-store.myshopify.com")
    mode, rest = a[0], a[1:]
    q, v = None, None
    if "--file" in rest:
        q = open(rest[rest.index("--file") + 1], encoding="utf-8").read()
    elif rest:
        q = rest[0]
    if "--vars" in rest:
        v = json.load(open(rest[rest.index("--vars") + 1], encoding="utf-8"))
    if not q:
        die("No query given.")
    is_mut = q.lstrip().startswith("mutation")
    if is_mut and mode != "mutate":
        die("This is a mutation: use the `mutate` command.")
    tok = token()
    if is_mut:
        guard(tok, q, v)
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(gql(tok, q, v), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
