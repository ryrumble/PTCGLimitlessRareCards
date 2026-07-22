"""
Fetch duplicate cross-references from card pages on LimitlessTCG.

For each card in duplicate_skip_cards, fetches the card page to find
cross-set same-card references. Adds the mapping to regulation_data.json.
"""

import json
import os
import re
import time

import requests
from bs4 import BeautifulSoup

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(REPO_ROOT, "regulation_data.json")

session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})


def fetch_duplicate_crossrefs(existing: dict) -> dict:
    """For each card in duplicate_skip_cards, fetch its page to find cross-set references."""
    dup_refs: dict = {}
    skip_cards = existing.get("duplicate_skip_cards", {})
    total = sum(len(nums) for nums in skip_cards.values())
    done = 0

    for set_code, numbers in skip_cards.items():
        for card_num in sorted(numbers):
            url = f"https://limitlesstcg.com/cards/{set_code}/{card_num}"
            try:
                resp = session.get(url, timeout=15)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.content, "html.parser")
                for a in soup.find_all("a", href=True):
                    m = re.match(r"/cards/([A-Z0-9]+)/(\d+)", a["href"])
                    if m and m.group(1) != set_code:
                        other_set = m.group(1)
                        other_num = int(m.group(2))
                        if set_code not in dup_refs:
                            dup_refs[set_code] = {}
                        if card_num not in dup_refs[set_code]:
                            dup_refs[set_code][card_num] = []
                        pair = (other_set, other_num)
                        if pair not in dup_refs[set_code][card_num]:
                            dup_refs[set_code][card_num].append(pair)
            except Exception:
                pass
            done += 1
            if done % 20 == 0:
                print(f"  Progress: {done}/{total}")
            time.sleep(3)

    print(f"  Complete: {done}/{total}")
    return dup_refs


def main():
    with open(DATA_FILE, encoding="utf-8") as f:
        existing = json.load(f)

    print("Fetching duplicate cross-references from card pages...")
    dup_refs = fetch_duplicate_crossrefs(existing)

    total_links = sum(len(refs) for set_code, cards in dup_refs.items() for card_num, refs in cards.items())
    print(f"Found {total_links} cross-references across {len(dup_refs)} sets")

    if dup_refs:
        existing["duplicate_crossrefs"] = dup_refs
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2)
        print(f"Updated {DATA_FILE}")


if __name__ == "__main__":
    main()
