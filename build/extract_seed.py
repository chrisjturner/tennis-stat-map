"""One-time seed extractor.

Reads the existing inline data out of index.html and writes a clean,
human-editable data/parents.json that becomes the source of truth for the
"Parents born in" view. Run once; after that you edit parents.json by hand.

    py build/extract_seed.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")

# The app is embedded in an iframe srcdoc, so its JS is HTML-entity-escaped.
def unescape(s: str) -> str:
    return (
        s.replace("&quot;", '"')
        .replace("&#x27;", "'")
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
    )

src = unescape(html)


def grab_initializer(name: str) -> str:
    """Return the `{...}`/`[...]` literal after `const NAME =`, brace-matched
    with awareness of string literals (values contain ';', '{', etc.)."""
    start = src.index(f"const {name} =")
    i = src.index("=", start) + 1
    while src[i].isspace():
        i += 1
    open_ch = src[i]
    close_ch = "}" if open_ch == "{" else "]"
    depth = 0
    in_str = False
    quote = ""
    j = i
    while j < len(src):
        ch = src[j]
        if in_str:
            if ch == "\\":
                j += 2
                continue
            if ch == quote:
                in_str = False
        elif ch in "\"'":
            in_str = True
            quote = ch
        elif ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return src[i : j + 1]
        j += 1
    raise ValueError(f"unbalanced initializer for {name}")


enriched = json.loads(grab_initializer("enriched"))
parent_origins = json.loads(grab_initializer("parentOrigins"))

# parentInferenceOverrides is a JS object literal with unquoted top-level keys.
ov_text = grab_initializer("parentInferenceOverrides")
ov_text = re.sub(r"(?<=[{\s])(atp|wta)\s*:", r'"\1":', ov_text)
overrides = json.loads(ov_text)

players = []
for tour in ("atp", "wta"):
    verified_by_rank = {o["r"]: o for o in parent_origins[tour]}
    for p in enriched[tour]:
        verified = verified_by_rank.get(p["r"])
        if verified:
            parents = [
                {
                    "role": "",            # fill in: father / mother
                    "name": o["p"],
                    "birthplace": o["bp"],
                    "country": o["bc"],
                    "status": "verified",
                    "source": "",          # fill in: URL(s) used to confirm
                }
                for o in verified["o"]
            ]
        elif p["n"] in overrides[tour]:
            # Old data only had country guesses, no names/places/sources.
            parents = [
                {"role": "", "name": "", "birthplace": "", "country": c,
                 "status": "inferred", "source": ""}
                for c in overrides[tour][p["n"]]
            ]
        else:
            parents = []  # no data yet -> "unknown" until researched
        players.append(
            {
                "tour": tour,
                "rank": p["r"],
                "name": p["n"],
                "represents": p["rep"],
                "birthplace": p["bp"],
                "birthCountry": p["bc"],
                "parents": parents,
                "note": p.get("f", ""),        # legacy free-text hint
                "researched": bool(verified),  # checked against sources yet?
            }
        )

out = {
    "_readme": (
        "Source of truth for the 'Parents born in' view. Edit this file, then "
        "run `py build/build_parents.py` to inject it into index.html and "
        "tennis-ranking-world-map.html. country = ISO 3166-1 alpha-3. status = "
        "verified (confirmed from a source) | inferred (best guess) | unknown. "
        "Add a source URL for verified entries; non-English sources are expected."
    ),
    "players": players,
}

(ROOT / "data").mkdir(exist_ok=True)
(ROOT / "data" / "parents.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"wrote data/parents.json with {len(players)} players")
