"""Collect each company's logo icon from its official website into logos/<slug>.png.

Order tried per company: the site's apple-touch-icon / large <link rel=icon>,
then /apple-touch-icon.png, then Google's favicon service (sz=256).
Images are normalised to a 256x256 PNG on a transparent canvas.
Writes logos/manifest.json listing which companies have a logo and its source.
"""
import io, json, os, re, sys, urllib.parse, urllib.request
from html.parser import HTMLParser
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "logos")
UA = {"User-Agent": "Mozilla/5.0 (FM Pulse UAE logo collector; +https://ananader1977.github.io/fm-pulse/)"}

def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def get(url, limit=3_000_000):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        if r.status != 200:
            raise ValueError(f"HTTP {r.status}")
        return r.read(limit), r.geturl()

class IconLinks(HTMLParser):
    def __init__(self):
        super().__init__(); self.icons = []
    def handle_starttag(self, tag, attrs):
        if tag != "link": return
        a = {k.lower(): (v or "") for k, v in attrs}
        rel = a.get("rel", "").lower()
        if "icon" in rel and a.get("href"):
            size = 0
            m = re.search(r"(\d+)x(\d+)", a.get("sizes", ""))
            if m: size = int(m.group(1))
            if "apple-touch-icon" in rel: size = max(size, 180)
            if a["href"].lower().endswith(".svg"): size = -1  # Pillow can't rasterise SVG
            self.icons.append((size, a["href"]))

def to_png(data):
    im = Image.open(io.BytesIO(data))
    if getattr(im, "n_frames", 1) > 1 and im.format == "ICO":
        im = max((im.ico.getimage(s) for s in im.ico.sizes()), key=lambda x: x.size[0])
    im = im.convert("RGBA")
    if min(im.size) < 48:
        raise ValueError(f"too small {im.size}")
    im.thumbnail((256, 256), Image.LANCZOS)
    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    canvas.paste(im, ((256 - im.size[0]) // 2, (256 - im.size[1]) // 2), im)
    buf = io.BytesIO(); canvas.save(buf, "PNG", optimize=True)
    return buf.getvalue(), im.size

def candidates(domain):
    urls = []
    for base in (f"https://www.{domain}/", f"https://{domain}/"):
        try:
            html, final = get(base, 800_000)
            p = IconLinks(); p.feed(html.decode("utf-8", "ignore"))
            for size, href in sorted(p.icons, key=lambda x: -x[0]):
                if size >= 0:
                    urls.append(urllib.parse.urljoin(final, href))
            urls.append(urllib.parse.urljoin(final, "/apple-touch-icon.png"))
            break
        except Exception as e:
            print(f"  homepage {base}: {e}")
    urls.append(f"https://www.google.com/s2/favicons?domain={domain}&sz=256")
    return urls

def main():
    os.makedirs(OUT, exist_ok=True)
    companies = json.load(open(os.path.join(ROOT, "tools", "companies.json")))
    manifest = {}
    for name, domain in companies.items():
        print(f"{name} ({domain})")
        for url in candidates(domain):
            try:
                data, _ = get(url)
                png, size = to_png(data)
                open(os.path.join(OUT, slug(name) + ".png"), "wb").write(png)
                manifest[name] = {"file": f"logos/{slug(name)}.png", "source": url, "size": list(size)}
                print(f"  OK {size} <- {url}")
                break
            except Exception as e:
                print(f"  skip {url}: {e}")
        else:
            print("  NO LOGO")
    json.dump(manifest, open(os.path.join(OUT, "manifest.json"), "w"), indent=2, sort_keys=True)
    print(f"\n{len(manifest)}/{len(companies)} logos saved")

if __name__ == "__main__":
    sys.exit(main())
