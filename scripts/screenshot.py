"""Full-page screenshots of a URL (reference page or your rebuilt page) at phone 390px and desktop 1440px.
Use them to compare the rebuild against the reference side by side.

  py -3 screenshot.py <url> <out-dir> [name]

Scrolls the whole page first (lazy images) and hides popups/modals before capturing.
Output: <out-dir>/<name>-phone.jpg and <out-dir>/<name>-desktop.jpg (screenshots are gitignored)."""
import asyncio
import base64
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cdp import Chrome  # noqa: E402

URL, OUT = sys.argv[1], pathlib.Path(sys.argv[2])
NAME = sys.argv[3] if len(sys.argv) > 3 else "page"
OUT.mkdir(parents=True, exist_ok=True)


async def shoot(ch, w, h0, mobile, label):
    await ch.viewport(w, h0, mobile)
    await ch.goto(URL)
    await asyncio.sleep(10)
    await ch.scroll_all(h0 // 2, 0.6)
    await ch.js("document.querySelectorAll('[class*=popup],[class*=modal],[id*=popup]').forEach(e=>e.style.display='none')")
    H = int(await ch.js("document.documentElement.scrollHeight"))
    await ch.viewport(w, min(H, 16000), mobile)
    await asyncio.sleep(4)
    r = await ch.call("Page.captureScreenshot", {"format": "jpeg", "quality": 70, "captureBeyondViewport": True})
    p = OUT / f"{NAME}-{label}.jpg"
    p.write_bytes(base64.b64decode(r["data"]))
    print(p, w, "x", H)


async def main():
    ch = Chrome()
    await ch.open_tab()
    try:
        await shoot(ch, 390, 844, True, "phone")
        await shoot(ch, 1440, 900, False, "desktop")
    finally:
        await ch.close()

asyncio.run(main())
