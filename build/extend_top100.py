"""One-time: extend data/parents.json from top-50 to top-100 per tour.

Player names for ranks 51-100 already live in the app's `tours[tour].names`
string (the ranking list powering the Represents/Age views). This pulls names
51-100 (and their represented country from `tours[tour].codes`) into
parents.json as new rows with empty parents, ready to research.

    py build/extend_top100.py
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
html = (ROOT / "index.html").read_text(encoding="utf-8")
src = (html.replace("&quot;", '"').replace("&#x27;", "'")
       .replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&"))

# tours = { atp: { date:"..", codes:"..", names:".." }, wta: {..} }
tours = {}
for tour in ("atp", "wta"):
    block = src[src.index(f"{tour}:", src.index("const tours =")):]
    codes = re.search(r'codes:\s*"([^"]*)"', block).group(1).split(",")
    names = re.search(r'names:\s*"([^"]*)"', block).group(1).split("|")
    tours[tour] = list(zip(names, codes))

data = json.loads((ROOT / "data" / "parents.json").read_text(encoding="utf-8"))
existing = {(p["tour"], p["rank"]) for p in data["players"]}

added = 0
for tour in ("atp", "wta"):
    for i in range(50, 100):  # ranks 51..100
        rank = i + 1
        if (tour, rank) in existing:
            continue
        name, rep = tours[tour][i]
        data["players"].append({
            "tour": tour, "rank": rank, "name": name, "represents": rep,
            "birthplace": "", "birthCountry": "", "parents": [],
            "note": "", "researched": False,
        })
        added += 1

# keep the file tidy: atp first, then wta, each by rank
data["players"].sort(key=lambda p: (p["tour"] != "atp", p["tour"], p["rank"]))

(ROOT / "data" / "parents.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"added {added} rows; total now {len(data['players'])}")
