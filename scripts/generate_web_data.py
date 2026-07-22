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
    """Construct the LimitlessTCG CDN URL for a card image."""
    return (
        f"https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/tpci/{set_code}/{set_code}_{card_number:03d}_R_EN_SM.png"
    )


def load_cache():
    path = os.path.join(REPO_ROOT, "cache.json")
    if not os.path.exists(path):
        print(f"Error: {path} not found. Run a scrape first.")
        sys.exit(1)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: cache.json is corrupt: {e}")
        sys.exit(1)


def export_cards(cache):
    cards = []
    for card_key, data in cache.get("cards", {}).items():
        match = re.match(r"^([A-Z0-9]+)_(\d+)$", card_key)
        if not match:
            continue
        set_code = match.group(1)
        card_number = int(match.group(2))
        reg = get_regulation(set_code, card_number)
        cards.append(
            {
                "s": set_code,
                "n": card_number,
                "c": data.get("card_name", "Unknown"),
                "d": data.get("decklist_count", 0),
                "t": data.get("latest_tournament") or "",
                "p": data.get("skip_permanent", False),
                "r": reg,
                "i": img_url(set_code, card_number),
            }
        )
    cards.sort(key=lambda x: (x["s"], x["n"]))
    return cards


def main():
    cache = load_cache()
    cards = export_cards(cache)

    out_dir = os.path.join(REPO_ROOT, "docs", "data")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cards.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(cards, f, separators=(",", ":"))

    print(f"Exported {len(cards)} cards to {os.path.relpath(out_path, REPO_ROOT)}")

    reg_counts = {}
    for c in cards:
        reg_counts[c["r"]] = reg_counts.get(c["r"], 0) + 1
    for reg in sorted(reg_counts):
        print(f"  Reg {reg}: {reg_counts[reg]} cards")

    set_codes = sorted(set(c["s"] for c in cards))
    print(f"Sets: {', '.join(set_codes)}")


if __name__ == "__main__":
    main()
