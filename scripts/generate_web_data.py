"""
Generate static JSON data for the GitHub Pages web viewer.

Reads cache.json and exports a simplified cards array to docs/data/cards.json.
Run this after scraping to refresh the web viewer data.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from regulation_filter import get_regulation

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def img_url(set_code, card_number):
    return (
        f"https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/tpci/{set_code}/{set_code}_{card_number:03d}_R_EN_SM.png"
    )


def load_cache():
    path = os.path.join(REPO_ROOT, "cache.json")
    if not os.path.exists(path):
        print(f"Error: {path} not found. Run a scrape first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_config():
    path = os.path.join(REPO_ROOT, "config.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_reg_data():
    path = os.path.join(REPO_ROOT, "regulation_data.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_duplicate_map(config, reg_data):
    """Build a reverse map: card_number -> [(set_code, card_number), ...]
    for every card that appears in any set's duplicate list."""
    dup_map: dict[int, list[tuple[str, int]]] = {}

    for set_code, numbers in reg_data.get("duplicate_skip_cards", {}).items():
        for n in numbers:
            if n not in dup_map:
                dup_map[n] = []
            dup_map[n].append((set_code, n))

    for set_code, set_data in config.get("sets", {}).items():
        for n in set_data.get("duplicate_skip_numbers", []):
            if n not in dup_map:
                dup_map[n] = []
            dup_map[n].append((set_code, n))

    return dup_map


def format_dup_refs(card_set, card_num, dup_map):
    """For a given card, return the list of duplicate refs as formatted strings.
    Excludes self-references. Returns ['SET NUM (REG)', ...]."""
    refs = dup_map.get(card_num, [])
    return sorted(f"{s} {n:03d} ({get_regulation(s, n)})" for s, n in refs if s != card_set)


def export_cards(cache, config, reg_data):
    dup_map = build_duplicate_map(config, reg_data)
    cards = []
    for card_key, data in cache.get("cards", {}).items():
        match = re.match(r"^([A-Z0-9]+)_(\d+)$", card_key)
        if not match:
            continue
        set_code = match.group(1)
        card_number = int(match.group(2))
        reg = get_regulation(set_code, card_number)
        entry = {
            "s": set_code,
            "n": card_number,
            "c": data.get("card_name", "Unknown"),
            "d": data.get("decklist_count", 0),
            "t": data.get("latest_tournament") or "",
            "p": data.get("skip_permanent", False),
            "r": reg,
            "i": img_url(set_code, card_number),
        }
        dups = format_dup_refs(set_code, card_number, dup_map)
        if dups:
            entry["u"] = dups  # duplicates
        cards.append(entry)
    cards.sort(key=lambda x: (x["s"], x["n"]))
    return cards


def main():
    cache = load_cache()
    config = load_config()
    reg_data = load_reg_data()
    cards = export_cards(cache, config, reg_data)

    out_dir = os.path.join(REPO_ROOT, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cards.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, separators=(",", ":"))

    # Stats
    total = len(cards)
    with_dups = sum(1 for c in cards if "u" in c)
    reg_counts: dict[str, int] = {}
    for c in cards:
        reg_counts[c["r"]] = reg_counts.get(c["r"], 0) + 1

    print(f"Exported {total} cards to {os.path.relpath(out_path, REPO_ROOT)}")
    print(f"  {with_dups} cards have duplicate references")
    for reg in sorted(reg_counts):
        print(f"  Reg {reg}: {reg_counts[reg]} cards")

    # Show example duplicates
    for c in cards:
        if "u" in c:
            print(f"\n  Example: {c['s']} {c['n']} ({c['r']}) -> duplicates: {c['u'][:3]}")
            break


if __name__ == "__main__":
    main()
