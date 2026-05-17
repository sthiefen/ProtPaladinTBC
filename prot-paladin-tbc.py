"""
WoW TBC Prot Paladin BIS Gear
=========================================================
Fetches item stats from Wowhead and computes
threat and mitigation scores using stat weights.

Usage:
    python prot-paladin-tbc.py

Output:
    prot-paladin-tbc.csv
"""

import json
import time
import csv
import re
import requests

# ---------------------------------------------------------------------------
# STAT WEIGHTS (from sixtyupgrades.com)
# ---------------------------------------------------------------------------

THREAT_WEIGHTS = {
    "stamina":          1.0,
    "intellect":        0.1,
    "strength":         0.024,
    "agility":          0.3,
    "dodgeRating":      0.26,
    "parryRating":      0.21,
    "defenseRating":    0.34,
    "blockRating":      0.63,
    "blockValue":       0.048,
    "blockValueBonus":  0.048,
    "hitRating":        0.1,
    "expertiseRating":  0.2,
    "spellDamage":      1.5,
    "spellHitRating":   0.1,
    "health":           0.08,
    "resilienceRating": 0.13,
    "armor":            0.05,
    "metaSockets":      18,
    "redSockets":       12,
    "yellowSockets":    12,
    "blueSockets":      12,
}

MITIGATION_WEIGHTS = {
    "stamina":          1.0,
    "intellect":        0.1,
    "strength":         0.022,
    "agility":          0.98,
    "dodgeRating":      1.06,
    "parryRating":      0.85,
    "defenseRating":    1.35,
    "blockRating":      2.54,
    "blockValue":       0.044,
    "blockValueBonus":  0.044,
    "hitRating":        0.1,
    "expertiseRating":  0.2,
    "spellDamage":      0.3,
    "spellHitRating":   0.1,
    "health":           0.08,
    "resilienceRating": 0.51,
    "armor":            0.05,
    "metaSockets":      18,
    "redSockets":       12,
    "yellowSockets":    12,
    "blueSockets":      12,
}

# ---------------------------------------------------------------------------
# BIS ITEM LIST  (name, wowhead_item_id, phase, slot)
# Phase: 0=Pre-Raid, 1=P1, 2=P2, 3=P3, 4=P4, 5=P5
# ---------------------------------------------------------------------------

BIS_ITEMS = [
    # Pre-Raid (Phase 0)
    ("Faceguard of Determination",      32083,  0, "Head"),
    ("Gladiator's Lamellar Helm",       31996,  0, "Head"),
    ("Devilshark Cape",                 27804,  0, "Back"),
    ("Bracers of Dignity",              29252,  0, "Wrist"),
    ("Vambraces of Courage",            28502,  0, "Wrist"),
    ("Iron Gauntlets of the Maiden",    28518,  0, "Hands"),
    ("Girdle of Valorous Deeds",        29253,  0, "Waist"),
    ("Boots of the Righteous Path",     29254,  0, "Feet"),
    ("Pendant of Dominance",            28245,  0, "Neck"),
    ("Ashyen's Gift",                   29172,  0, "Ring"),
    ("Seal of the Exorcist",            28555,  0, "Ring"),
    ("Andormu's Tear",                  29323,  0, "Ring"),
    ("Gladiator's Gavel",               32450,  0, "Weapon"),
    ("Gavel of Unearthed Secrets",      30832,  0, "Weapon"),

    # Phase 1
    ("Justicar Faceguard",              29068,  1, "Head"),
    ("Crystalforge Faceguard",          30125,  2, "Head"),  # appears P2 BiS head
    ("Tankatronic Goggles",             32473,  2, "Head"),
    ("Justicar Shoulderguards",         29070,  1, "Shoulder"),
    ("Gilded Thorium Cloak",            28660,  1, "Back"),
    ("Ruby Drape of the Mysticant",     28766,  1, "Back"),
    ("Justicar Chestguard",             29066,  1, "Chest"),
    ("Panzar'Thar Breastplate",         28597,  1, "Chest"),
    ("Crystalforge Chestguard",         30123,  2, "Chest"),
    ("Wristguards of Determination",    32515,  2, "Wrist"),
    ("Justicar Handguards",             29067,  1, "Hands"),
    ("Crimson Girdle of the Indomitable", 28566, 1, "Waist"),
    ("Girdle of the Invulnerable",      30096,  2, "Waist"),
    ("Belt of the Guardian",            30034,  2, "Waist"),
    ("Wrynn Dynasty Greaves",           28621,  1, "Legs"),
    ("Justicar Legguards",              29069,  1, "Legs"),
    ("Crystalforge Legguards",          30126,  2, "Legs"),
    ("Boots of Elusion",                30641,  1, "Feet"),
    ("Battlescar Boots",                28747,  1, "Feet"),
    ("Boots of the Resilient",          32267,  2, "Feet"),
    ("Boots of the Protector",          30033,  2, "Feet"),
    ("Barbed Choker of Discipline",     28516,  1, "Neck"),
    ("Brooch of Unquenchable Fury",     28530,  1, "Neck"),
    ("The Darkener's Grasp",            30007,  2, "Neck"),
    ("Elementium Band of the Sentry",   28407,  1, "Ring"),
    ("Violet Signet of the Great Protector", 29279, 1, "Ring"),
    ("Ring of Sundered Souls",          30083,  2, "Ring"),
    ("Seventh Ring of the Tirisfalen",  30028,  2, "Ring"),
    ("The Seal of Danzalar",            33054,  2, "Ring"),
    ("Bloodmaw Magus-Blade",            28802,  1, "Weapon"),
    ("Merciless Gladiator's Gavel",     32963,  2, "Weapon"),
    ("Fang of the Leviathan",           30095,  2, "Weapon"),

    # Phase 3
    ("Faceplate of the Impenetrable",   32521,  3, "Head"),
    ("Lightbringer Faceguard",          30987,  3, "Head"),
    ("Lightbringer Shoulderguards",     30998,  3, "Shoulder"),
    ("Pepe's Shroud of Pacification",   34010,  3, "Back"),
    ("Phoenix-Wing Cloak",              29925,  2, "Back"),
    ("Royal Cloak of the Sunstriders",  29992,  2, "Back"),
    ("Lightbringer Chestguard",         30991,  3, "Chest"),
    ("The Seeker's Wristguards",        32279,  3, "Wrist"),
    ("Eternium Shell Bracers",          32232,  3, "Wrist"),
    ("Lightbringer Handguards",         30985,  3, "Hands"),
    ("Royal Gauntlets of Silvermoon",   29998,  2, "Hands"),
    ("Crystalforge Handguards",         30124,  2, "Hands"),
    ("Girdle of Mighty Resolve",        32342,  3, "Waist"),
    ("Lightbringer Legguards",          30995,  3, "Legs"),
    ("Praetorian's Legguards",          32263,  3, "Legs"),
    ("Tide-stomper's Greaves",          32245,  3, "Feet"),
    ("Pendant of Titans",               32362,  3, "Neck"),
    ("Band of the Abyssal Lord",        32261,  3, "Ring"),
    ("Tempest of Chaos",                30910,  3, "Weapon"),
    ("Vengeful Gladiator's Gavel",      33687,  3, "Weapon"),

    # Phase 4
    ("Battleworn Tuskguard",            33421,  4, "Head"),
    ("Pauldrons of Stone Resolve",      33481,  4, "Shoulder"),
    ("Slikk's Cloak of Placation",      33593,  4, "Back"),
    ("Chestguard of the Warlord",       33473,  4, "Chest"),
    ("Chestguard of the Stoic Guardian", 33522, 4, "Chest"),
    ("Bracers of the Ancient Phalanx",  34436,  4, "Wrist"),
    ("Bonefist Gauntlets",              33517,  4, "Hands"),
    ("Girdle of the Protector",         33524,  4, "Waist"),
    ("Unwavering Legguards",            33515,  4, "Legs"),
    ("Sabatons of the Righteous Defender", 33523, 4, "Feet"),
    ("Jungle Stompers",                 33191,  4, "Feet"),
    ("Amani Punisher",                  33283,  4, "Weapon"),

    # Phase 5
    ("Helm of Uther's Resolve",         34401,  5, "Head"),
    ("Crown of Dath'Remar",             34400,  5, "Head"),
    ("Spaulders of the Thalassian Defender", 34389, 5, "Shoulder"),
    ("Pauldrons of Perseverance",       34192,  5, "Shoulder"),
    ("Crimson Paragon's Cover",         34190,  5, "Back"),
    ("Heroic Judicator's Chestguard",   34216,  5, "Chest"),
    ("Shattrath Protectorate's Breastplate", 34945, 5, "Chest"),
    ("Lightbringer Wristguards",        34433,  5, "Wrist"),
    ("Borderland Fortress Grips",       34352,  5, "Hands"),
    ("Lightbringer Waistguard",         34488,  5, "Waist"),
    ("Judicator's Legguards",           34382,  5, "Legs"),
    ("Lightbringer Stompers",           34560,  5, "Feet"),
    ("Blue's Greaves of the Righteous Guardian", 34947, 5, "Feet"),
    ("Collar of the Pit Lord",          34178,  5, "Neck"),
    ("Ring of Hardened Resolve",        34213,  5, "Ring"),
    ("Ring of the Stalwart Protector",  34888,  5, "Ring"),
    ("Fused Nethergon Band",            34889,  5, "Ring"),
    ("Brutal Gladiator's Gavel",        35014,  5, "Weapon"),
    ("Reign of Misery",                 34176,  5, "Weapon"),
]

# ---------------------------------------------------------------------------
# WOWHEAD STAT NAME -> weight key mapping
# ---------------------------------------------------------------------------

# Maps substrings found in Wowhead tooltip text to our weight keys
STAT_PATTERNS = [
    (r"\+(\d+) Stamina",                        "stamina"),
    (r"\+(\d+) Intellect",                      "intellect"),
    (r"\+(\d+) Strength",                       "strength"),
    (r"\+(\d+) Agility",                        "agility"),
    (r"dodge rating by (\d+)",                  "dodgeRating"),
    (r"parry rating by (\d+)",                  "parryRating"),
    (r"defense rating by (\d+)",                "defenseRating"),
    (r"(?:shield )?block rating by (\d+)",      "blockRating"),
    (r"block value by (\d+)",                   "blockValue"),
    (r"hit rating by (\d+)",                    "hitRating"),
    (r"expertise rating by (\d+)",              "expertiseRating"),
    (r"spell (?:hit|critical strike)? ?hit rating by (\d+)", "spellHitRating"),
    (r"spell critical strike rating by (\d+)",  "spellCritRating"),  # not in weights — ignore
    (r"resilience rating by (\d+)",             "resilienceRating"),
    (r"damage and healing.*?by up to (\d+)",    "spellDamage"),
    (r"healing.*?by up to (\d+)",               "spellDamage"),
]

SOCKET_PATTERNS = [
    (r"Meta Socket",    "metaSockets"),
    (r"Red Socket",     "redSockets"),
    (r"Yellow Socket",  "yellowSockets"),
    (r"Blue Socket",    "blueSockets"),
]

# ---------------------------------------------------------------------------
# FETCHING
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; WoW-BIS-Fetcher/1.0)"
})

def fetch_item_page(item_id: int) -> str | None:
    """Fetch the Wowhead TBC item page and return its text content."""
    url = f"https://www.wowhead.com/tbc/item={item_id}"
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  ERROR fetching item {item_id}: {e}")
        return None


def parse_stats(html: str, item_id: int) -> dict:
    """
    Parse stat values from the Wowhead item page HTML.
    Returns a dict of {weight_key: value}.

    Extracts jsonequip from the WH.Gatherer.addData JS call and reads
    stats as structured numeric fields — no regex on tooltip text.
    """
    stats = {}

    # Wowhead embeds item data across multiple WH.Gatherer.addData(3, 5, {...}) calls.
    # Search all blocks until we find the one containing our item_id.
    blocks = re.findall(r'WH\.Gatherer\.addData\(3,\s*5,\s*(\{.*?\})\s*\);', html, re.DOTALL)
    if not blocks:
        print(f"  WARNING: WH.Gatherer.addData not found")
        return stats

    item_data = None
    for block in blocks:
        try:
            data = json.loads(block)
            if str(item_id) in data:
                item_data = data[str(item_id)]
                break
        except json.JSONDecodeError:
            continue

    if not item_data:
        print(f"  WARNING: item {item_id} not found in any Gatherer block")
        return stats

    je = item_data.get("jsonequip", {})
    print(f"  jsonequip: {je}")

    field_map = {
        "sta":        "stamina",
        "int":        "intellect",
        "str":        "strength",
        "agi":        "agility",
        "dodgertng":  "dodgeRating",
        "parrytng":   "parryRating",
        "defrtng":    "defenseRating",
        "blockrtng":  "blockRating",
        "block":      "blockValue",
        "hitrtng":    "hitRating",
        "exprtng":    "expertiseRating",
        "spldmg":     "spellDamage",
        "splhitrtng": "spellHitRating",
        "health":     "health",
        "resirtng":   "resilienceRating",
        "armor":      "armor",
    }
    for je_key, weight_key in field_map.items():
        val = je.get(je_key, 0) or 0
        if val:
            stats[weight_key] = float(val)

    # Sockets: 1=meta, 2=red, 3=yellow, 4=blue
    socket_map = {1: "metaSockets", 2: "redSockets", 3: "yellowSockets", 4: "blueSockets"}
    n = je.get("nsockets", 0) or 0
    for i in range(1, n + 1):
        key = socket_map.get(je.get(f"socket{i}"))
        if key:
            stats[key] = stats.get(key, 0) + 1

    return stats


def compute_score(stats: dict, weights: dict) -> float:
    """Compute a weighted score from parsed stats."""
    total = 0.0
    for key, weight in weights.items():
        total += stats.get(key, 0) * weight
    return round(total, 1)


def wowhead_url(item_id: int, name: str) -> str:
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"https://www.wowhead.com/tbc/item={item_id}/{slug}"


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

PHASE_LABELS = {
    0: "Pre-Raid",
    1: "Phase 1",
    2: "Phase 2",
    3: "Phase 3",
    4: "Phase 4",
    5: "Phase 5",
}

OUTPUT_FILE = "prot-paladin-tbc.csv"

def main():
    results = []
    total = len(BIS_ITEMS)

    print(f"Fetching {total} items from Wowhead...\n")

    for i, (name, item_id, phase, slot) in enumerate(BIS_ITEMS, 1):
        print(f"[{i}/{total}] {name} (id={item_id})")
        html = fetch_item_page(item_id)

        if html is None:
            print(f"  Skipping — could not fetch page.")
            results.append({
                "name": name,
                "item_id": item_id,
                "phase": PHASE_LABELS[phase],
                "slot": slot,
                "threat": "ERROR",
                "mitigation": "ERROR",
                "url": wowhead_url(item_id, name),
            })
            time.sleep(1)
            continue

        stats = parse_stats(html, item_id)
        threat = compute_score(stats, THREAT_WEIGHTS)
        mitigation = compute_score(stats, MITIGATION_WEIGHTS)

        print(f"  Stats found: {stats}")
        print(f"  → Threat: {threat}  |  Mitigation: {mitigation}")

        results.append({
            "name": name,
            "item_id": item_id,
            "phase": PHASE_LABELS[phase],
            "slot": slot,
            "threat": threat,
            "mitigation": mitigation,
            "url": wowhead_url(item_id, name),
        })

        # Be polite to Wowhead — don't hammer the server
        time.sleep(0.25)

    # Write CSV
    fieldnames = ["name", "phase", "slot", "threat", "mitigation", "url", "item_id"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row[k] for k in fieldnames})

    print(f"\nDone! Results written to {OUTPUT_FILE}")
    print(f"Paste the CSV contents into a new Claude conversation to render the scatter plots.")


if __name__ == "__main__":
    main()
