"""Find each news story's preview image (og:image / twitter:image) and save the URLs.

Reads the news snapshot embedded in index.html, visits each story's source page,
and writes images/news-images.json: {doc_id: {"img": url, "credit": domain}}.
Only image URLs are stored; images are displayed from the publisher with a credit
and a link back to the story. Hiring items and homepage links are skipped.
"""
import io, json, os, re, sys, urllib.parse, urllib.request
from html.parser import HTMLParser
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "images", "news-images.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; FMPulseUAE-preview/1.0; +https://ananader1977.github.io/fm-pulse/)",
      "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}

def get(url, limit):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(limit), r.geturl(), r.headers.get("Content-Type", "")

class Meta(HTMLParser):
    def __init__(self):
        super().__init__(); self.found = {}
    def handle_starttag(self, tag, attrs):
        if tag != "meta": return
        a = {k.lower(): (v or "") for k, v in attrs}
        key = (a.get("property") or a.get("name") or "").lower()
        if key in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src") and a.get("content"):
            self.found.setdefault(key, a["content"].strip())

BAD = ("logo", "favicon", "placeholder", "default-og", "static.tradingview.com", "share-default")
def generic(img):
    low = img.lower()
    return any(b in low for b in BAD)

def snapshot():
    html = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="snapshot">(.*?)</script>', html, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))["items"]

def main():
    items = snapshot()
    try:
        old = json.load(open(OUT))
    except Exception:
        old = {}
    result, cache = {}, {}
    for n in items:
        nid, url = n.get("id"), n.get("url", "")
        if not nid or not url.startswith("http"): continue
        if n.get("type") == "Hiring": continue
        path = urllib.parse.urlparse(url).path
        if path in ("", "/") or path.rstrip("/").count("/") < 1 and len(path) < 3: continue
        if nid in old and not generic(old[nid].get("img", "")):   # keep earlier finds; don't re-fetch daily
            result[nid] = old[nid]; continue
        if url in cache:
            if cache[url]: result[nid] = cache[url]
            continue
        cache[url] = None
        try:
            html, final, _ = get(url, 600_000)
            p = Meta(); p.feed(html.decode("utf-8", "ignore"))
            img = next((p.found[k] for k in ("og:image:secure_url", "og:image", "twitter:image", "twitter:image:src") if k in p.found), "")
            if not img: print(f"- {nid}: no preview image"); continue
            img = urllib.parse.urljoin(final, img)
            if not img.startswith("https://"): print(f"- {nid}: not https"); continue
            if generic(img): print(f"- {nid}: generic site image"); continue
            data, _, ctype = get(img, 4_000_000)
            w, h = Image.open(io.BytesIO(data)).size
            if w < 400 or h < 180 or w / h > 3.2 or h / w > 1.6:
                print(f"- {nid}: unsuitable size {w}x{h}"); continue
            credit = urllib.parse.urlparse(final).netloc.replace("www.", "")
            cache[url] = {"img": img, "credit": credit, "w": w, "h": h}
            result[nid] = cache[url]
            print(f"+ {nid}: {w}x{h} {img[:90]}")
        except Exception as e:
            print(f"- {nid}: {e}")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(result, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"\n{len(result)} stories with preview images")

if __name__ == "__main__":
    sys.exit(main())
