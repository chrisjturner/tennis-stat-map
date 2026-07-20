"""Inject data/parents.json into the app.

Reads the clean source-of-truth (data/parents.json), builds the compact
`parentProfiles` structure the app consumes, and rewrites the data block inside
both index.html and tennis-ranking-world-map.html (which is the GitHub Pages
copy). The app can't fetch JSON at runtime (its CSP blocks network), so the data
has to be inlined here at build time.

    py build/build_parents.py

Edit parents.json, run this, commit both HTML files.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "parents.json").read_text(encoding="utf-8"))
# index.html is canonical; the Pages copy is kept byte-identical to it.
CANONICAL = "index.html"
COPIES = ["tennis-ranking-world-map.html"]

START = "/*PARENTS:GENERATED — edit data/parents.json then run: py build/build_parents.py*/"
END = "/*END PARENTS*/"


def player_status(parents):
    if not parents:
        return "unknown"
    if all(p["status"] == "verified" for p in parents):
        return "verified"
    return "inferred"


def build_profiles():
    profiles = {"atp": [], "wta": []}
    for pl in DATA["players"]:
        origins = []
        for p in pl["parents"]:
            verified = p["status"] == "verified"
            origins.append(
                {
                    "p": p["name"] or "Parent",
                    # detail strings read "... born {bp}"; give inferred rows a
                    # sensible phrase when no specific place is known.
                    "bp": p["birthplace"] or ("family background" if not verified else ""),
                    "bc": p["country"],
                    "s": p["status"],
                }
            )
        profiles[pl["tour"]].append(
            {"r": pl["rank"], "n": pl["name"], "status": player_status(pl["parents"]), "o": origins}
        )
    for tour in profiles:
        profiles[tour].sort(key=lambda e: e["r"])
    return profiles


def html_escape(s: str) -> str:
    # Match the escaping used inside the iframe srcdoc attribute.
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def find_region(html: str):
    """Return (start_idx, end_idx) of the block to replace.

    On the first run there are no markers, so we match the three original
    declarations (parentOrigins, parentInferenceOverrides, and the
    parentProfiles builder). Afterwards we replace between our markers.
    """
    if START in html:
        s = html.index(START)
        e = html.index(END, s) + len(END)
        return s, e
    s = html.index("const parentOrigins =")
    # The original block ends at the parentProfiles builder's `})]));`.
    marker = "})]));"
    e = html.index(marker, html.index("const parentProfiles =")) + len(marker)
    return s, e


def main():
    profiles = build_profiles()
    payload = json.dumps(profiles, ensure_ascii=False, separators=(",", ":"))
    block = f"{START}\n    const parentProfiles = {html_escape(payload)};\n    {END}"

    path = ROOT / CANONICAL
    html = path.read_text(encoding="utf-8")
    s, e = find_region(html)
    html = html[:s] + block + html[e:]
    path.write_text(html, encoding="utf-8")
    for name in COPIES:
        (ROOT / name).write_text(html, encoding="utf-8")

    counts = {
        t: {
            k: sum(1 for pl in profiles[t] if pl["status"] == k)
            for k in ("verified", "inferred", "unknown")
        }
        for t in ("atp", "wta")
    }
    print(f"updated {CANONICAL} + {COPIES}: {counts}")


if __name__ == "__main__":
    main()
