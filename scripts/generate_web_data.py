"""
Generate static JSON data for the GitHub Pages web viewer.

Reads cache.json and exports a simplified cards array to docs/data/cards.json.
Merges duplicate cards (same card across different sets) into single rows.
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


def build_alias_map(reg_data):
    """
    Build a mapping from (set, number) to a list of all alias (set, number) pairs.

    Uses duplicate_crossrefs (fetched from card pages) to determine which cards
    are the same across sets. Returns {canonical_key: [alias_keys, ...]} and
    a set of all alias keys that should be skipped.
    """
    crossrefs = reg_data.get("duplicate_crossrefs", {})

    # Build graph: each cross-ref is an edge between two cards
    # key = "SET_NUM"
    graph: dict[str, set[str]] = {}
    all_aliases: set[str] = set()

    for set_code, cards in crossrefs.items():
        for card_num, refs in cards.items():
            key = f"{set_code}_{card_num}"
            if key not in graph:
                graph[key] = set()
            all_aliases.add(key)
            for other_set, other_num in refs:
                other_key = f"{other_set}_{other_num}"
                if other_key not in graph:
                    graph[other_key] = set()
                graph[key].add(other_key)
                graph[other_key].add(key)

    # For each alias, find its canonical card (the one that's NOT an alias)
    # If all connected cards are aliases, pick the first alphabetically
    alias_to_canonical: dict[str, str] = {}

    for alias_key in all_aliases:
        # Find the component (all connected nodes)
        component = set()
        stack = [alias_key]
        while stack:
            k = stack.pop()
            if k in component:
                continue
            component.add(k)
            for neighbor in graph.get(k, []):
                if neighbor not in component:
                    stack.append(neighbor)

        # Pick canonical: the key that's NOT an alias (i.e., not in duplicate_skip_cards)
        skip_cards = reg_data.get("duplicate_skip_cards", {})
        canonical = None
        for k in sorted(component):
            s, n_str = k.split("_", 1)
            n = int(n_str)
            if s not in skip_cards or n not in skip_cards[s]:
                canonical = k
                break
        if canonical is None:
            canonical = sorted(component)[0]

        alias_to_canonical[alias_key] = canonical

    return alias_to_canonical, all_aliases


def export_cards(cache, config, reg_data):
    alias_map, alias_set = build_alias_map(reg_data)

    # Group cards by canonical key
    groups: dict[str, dict] = {}

    for card_key, data in cache.get("cards", {}).items():
        match = re.match(r"^([A-Z0-9]+)_(\d+)$", card_key)
        if not match:
            continue
        set_code = match.group(1)
        card_number = int(match.group(2))

        # If this card is an alias, skip it (canonical row will include it)
        if card_key in alias_set:
            # Still need to check if this IS the canonical for itself
            canonical = alias_map[card_key]
            if canonical != card_key:
                continue  # not the canonical, skip

        # Build the entry
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

        # Collect aliases for this canonical card
        aliases = []
        for alias_key in sorted(alias_set):
            if alias_map.get(alias_key) == card_key:
                s, n_str = alias_key.split("_", 1)
                n = int(n_str)
                aliases.append(f"{s} {n:03d} ({get_regulation(s, n)})")
        if aliases:
            entry["u"] = aliases

        groups[card_key] = entry

    # Sort by set then number
    cards = sorted(groups.values(), key=lambda x: (x["s"], x["n"]))
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
    skipped = len(cache.get("cards", {})) - total
    reg_counts: dict[str, int] = {}
    for c in cards:
        reg_counts[c["r"]] = reg_counts.get(c["r"], 0) + 1

    print(f"Exported {total} cards to {os.path.relpath(out_path, REPO_ROOT)}")
    print(f"  Merged {skipped} duplicate cards into canonical rows")
    print(f"  {with_dups} rows have duplicate aliases")
    for reg in sorted(reg_counts):
        print(f"  Reg {reg}: {reg_counts[reg]} cards")

    # Show example
    for c in cards:
        if "u" in c:
            print(f"\n  Example: {c['s']} {c['n']} ({c['r']}) -> also: {c['u'][:3]}")
            break


if __name__ == "__main__":
    main()
