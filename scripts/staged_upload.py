"""Upload local files to Shopify through a staged upload (the step between stagedUploadsCreate and fileCreate).

  py -3 staged_upload.py <stagedUploadsCreate-result.json> <dir-with-files>

The JSON is the "stagedTargets" part (or the whole response) of the stagedUploadsCreate mutation
(request `url`, `resourceUrl` and `parameters { name value }`). For each target the script finds the file with the
same name in <dir-with-files> (name = last segment of resourceUrl), POSTs it as multipart to the bucket, and prints
the HTTP status (201/204 = OK) plus resourceUrl, which you then pass to
fileCreate(files:[{originalSource: <resourceUrl>, contentType: FILE, filename}]).

Note: stagedUploadsCreate names the target after the `filename` you requested, so request it with the local name."""
import json
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

raw = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))


def find_targets(o):
    if isinstance(o, dict):
        if "stagedTargets" in o:
            return o["stagedTargets"]
        for v in o.values():
            r = find_targets(v)
            if r:
                return r
    return None


targets = find_targets(raw) or raw
folder = pathlib.Path(sys.argv[2])
for t in targets:
    name = t["resourceUrl"].rstrip("/").rsplit("/", 1)[-1].split("?")[0]
    data = (folder / name).read_bytes()
    b = uuid.uuid4().hex
    body = b""
    for p in t["parameters"]:
        body += f'--{b}\r\nContent-Disposition: form-data; name="{p["name"]}"\r\n\r\n{p["value"]}\r\n'.encode("utf-8")
    body += (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n\r\n'.encode("utf-8")
             + data + f"\r\n--{b}--\r\n".encode("utf-8"))
    req = urllib.request.Request(t.get("url") or "https://shopify-staged-uploads.storage.googleapis.com/", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            print(r.status, name, t["resourceUrl"])
    except urllib.error.HTTPError as e:
        print(e.code, name, e.read()[:200])
