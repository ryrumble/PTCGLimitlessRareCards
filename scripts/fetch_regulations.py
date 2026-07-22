"""
Fetch regulation search pages from LimitlessTCG to build a per-card regulation mapping.

Each URL filters by regulation letter. Every card link on the page belongs to that regulation.
This is a ONE-TIME data build. Results committed to regulation_data.json.
"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(REPO_ROOT, "regulation_data.json")

REGULATION_URLS = {
    "G": "https://limitlesstcg.com/cards?q=reg%3Ag&unique=prints&sort=set&show=all",
    "H": "https://limitlesstcg.com/cards?q=reg%3Ah&unique=prints&sort=set&show=all",
    "I": "https://limitlesstcg.com/cards?q=reg%3Ai&unique=prints&sort=set&show=all",
    "J": "https://limitlesstcg.com/cards?q=reg%3Aj&unique=prints&sort=set&show=all",
}


def fetch_regulation_cards(reg: str, session: requests.Session) -> dict[str, set[int]]:
    """Fetch all cards for a given regulation letter. Returns {set: {card_numbers}}."""
    url = REGULATION_URLS[reg]
    print(f"Fetching regulation {reg}...")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    cards: dict[str, set[int]] = {}
    for a in soup.find_all("a", href=True):
        m = re.match(r"/cards/([A-Z0-9]+)/(\d+)", a["href"])
        if m:
            set_code = m.group(1)
            card_num = int(m.group(2))
            if set_code not in cards:
                cards[set_code] = set()
            cards[set_code].add(card_num)

    total = sum(len(nums) for nums in cards.values())
    print(f"  Found {total} cards in {len(cards)} sets")
    return cards


def fetch_regulation_from_card_page(set_code: str, card_num: int, session: requests.Session) -> str | None:
    """Fetch a single card page and extract its regulation mark."""
    url = f"https://limitlesstcg.com/cards/{set_code}/{card_num}"
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        html = resp.text
        m = re.search(r"([A-Z])\s*Regulation\s*Mark", html)
        if m:
            return m.group(1)
    except Exception:
        pass
    return None


def main():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})

    all_reg_cards: dict[str, dict[str, set[int]]] = {}
    for reg in ["G", "H", "I", "J"]:
        cards = fetch_regulation_cards(reg, session)
        all_reg_cards[reg] = cards
        time.sleep(3)

    # Load existing data
    with open(DATA_FILE, encoding="utf-8") as f:
        existing = json.load(f)

    # Build per-card regulation mapping from search pages
    per_card: dict[str, dict[str, str]] = {}
    for reg, sets in all_reg_cards.items():
        for set_code, numbers in sets.items():
            if set_code not in per_card:
                per_card[set_code] = {}
            for n in numbers:
                per_card[set_code][str(n)] = reg

    # Handle SVP cards: fetch each card page for regulation mark
    # Read from existing cache to find which SVP cards we have
    cache_file = os.path.join(REPO_ROOT, "cache.json")
    if os.path.exists(cache_file):
        import re as re_cache

        with open(cache_file, encoding="utf-8") as f:
            cache = json.load(f)
        svp_cards = []
        for key in cache.get("cards", {}):
            m = re_cache.match(r"^SVP_(\d+)$", key)
            if m:
                svp_cards.append(int(m.group(1)))
        svp_cards.sort()

        fetched = 0
        for cn in svp_cards:
            key = str(cn)
            if "SVP" in per_card and key in per_card["SVP"]:
                continue  # already mapped
            reg = fetch_regulation_from_card_page("SVP", cn, session)
            if reg:
                if "SVP" not in per_card:
                    per_card["SVP"] = {}
                per_card["SVP"][key] = reg
                fetched += 1
                print(f"  SVP {cn} -> {reg}")
            time.sleep(3)  # rate limit
        print(f"Fetched regulation for {fetched} SVP cards")

    existing["per_card_regulation"] = per_card

    # Update set_regulation
    set_reg: dict[str, list[str]] = {}
    for reg in ["G", "H", "I", "J"]:
        key = f"Regulation {reg}"
        set_reg[key] = sorted(all_reg_cards[reg].keys())
    existing["set_regulation"] = set_reg

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)

    total_cards = sum(len(nums) for sets in per_card.values() for nums in sets.values())
    print(f"\nTotal cards mapped by regulation: {total_cards}")
    for reg in ["G", "H", "I", "J"]:
        count = sum(len(all_reg_cards[reg][s]) for s in all_reg_cards[reg])
        print(f"  Reg {reg}: {count} cards")

    svp_mapped = len(per_card.get("SVP", {}))
    svp_unknown = sum(1 for k in per_card.get("SVP", {}).values() if k == "?")
    print(f"  SVP: {svp_mapped} mapped ({svp_unknown} unknown)")

    print(f"\nUpdated {DATA_FILE}")


if __name__ == "__main__":
    main()
