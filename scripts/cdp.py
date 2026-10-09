"""Minimal Chrome DevTools Protocol client: open a tab, navigate, run JS, emulate a viewport, screenshot.

Needs a Chrome started with a remote-debugging port. Default port 9230, override with env CDP_PORT.
Use a DEDICATED Chrome profile so you never disturb the user's normal browser or other automation:

  Windows:  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9230 --user-data-dir=%TEMP%\\ppc-chrome
  macOS:    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9230 --user-data-dir=/tmp/ppc-chrome
  Linux:    google-chrome --remote-debugging-port=9230 --user-data-dir=/tmp/ppc-chrome

Requires: pip install websockets
"""
import asyncio
import json
import os
import urllib.request

import websockets

PORT = int(os.environ.get("CDP_PORT") or 9230)


class Chrome:
    def __init__(self, port: int = PORT):
        self.port, self.ws, self.target_id, self._id = port, None, None, 0

    def _http(self, path, method="GET"):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    async def open_tab(self):
        """Open a fresh tab (always close it with close() so no stray tabs are left behind)."""
        tab = self._http("/json/new?about:blank", method="PUT")
        self.target_id = tab["id"]
        self.ws = await websockets.connect(tab["webSocketDebuggerUrl"], max_size=64 * 1024 * 1024, ping_interval=None)
        await self.call("Page.enable")
        await self.call("Runtime.enable")

    async def call(self, method, params=None, timeout=60.0):
        self._id += 1
        mid = self._id
        await self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(await asyncio.wait_for(self.ws.recv(), timeout=timeout))
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    async def goto(self, url):
        await self.call("Page.navigate", {"url": url})

    async def js(self, expr, timeout=60.0):
        r = await self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True}, timeout=timeout)
        if r.get("exceptionDetails"):
            raise RuntimeError(str(r["exceptionDetails"])[:400])
        return r.get("result", {}).get("value")

    async def viewport(self, w, h, mobile):
        await self.call("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": mobile})

    async def scroll_all(self, step=450, wait=0.5):
        """Scroll the page in steps so lazy images load, then return to the top."""
        H = await self.js("document.documentElement.scrollHeight")
        y = 0
        while y < H:
            await self.js(f"window.scrollTo(0,{y})")
            await asyncio.sleep(wait)
            y += step
            H = await self.js("document.documentElement.scrollHeight")
        await self.js("window.scrollTo(0,0)")
        await asyncio.sleep(1.5)

    async def close(self):
        try:
            if self.ws:
                await self.ws.close()
        except Exception:
            pass
        try:
            if self.target_id:
                self._http(f"/json/close/{self.target_id}")
        except Exception:
            pass
