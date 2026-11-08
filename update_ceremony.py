#!/usr/bin/env python3
"""One-off: replace the order of ceremony in YOUR wedding.json with the 8 updated steps,
keeping everything else in the file as it is."""
import json
from pathlib import Path
p = Path(__file__).with_name("wedding.json")
d = json.loads(p.read_text(encoding="utf-8"))
d.setdefault("programme", {})["items"] = [
    {"ta": "திருவிளக்கு ஏற்றுதல்", "en": "Lighting of the sacred lamp"},
    {"ta": "விநாயகர் வழிபாடு", "en": "Prayer to Lord Ganesha"},
    {"ta": "கலச வழிபாடு", "en": "Worship of the sacred kalasam"},
    {"ta": "வேள்வி / திருமுறை ஓதுதல்", "en": "Sacred fire and Thirumurai hymns"},
    {"ta": "மாங்கல்யம் அணிவித்தல்", "en": "Tying of the Thali"},
    {"ta": "மணவறை வலம்", "en": "Circling the wedding dais"},
    {"ta": "கதிரவன் வழிபாடு", "en": "Prayer to the Sun"},
    {"ta": "மணமக்கள் வாழ்த்து", "en": "Blessing the couple"},
]
p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Updated order of ceremony in", p)
