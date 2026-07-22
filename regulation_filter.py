"""
Regulation Format Filter

This module provides functionality to determine if a card is in G regulation format,
which is used to filter out rotating cards from searches and displays.

Regulation data is loaded from regulation_data.json so it can be updated
without code changes.
"""

import json
import os


def _load_regulation_data() -> dict:
    """Load regulation data from JSON file next to this module."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(module_dir, "regulation_data.json")
    with open(data_file, encoding="utf-8") as f:
        return json.load(f)


_reg_data = _load_regulation_data()

FULL_G_REGULATION_SETS: set[str] = set(_reg_data["full_g_regulation_sets"])
FULL_I_REGULATION_SETS: set[str] = set(_reg_data["full_i_regulation_sets"])

MIXED_SET_G_CARDS: dict[str, set[int]] = {}
for set_code, cfg in _reg_data["mixed_set_g_cards"].items():
    if "include" in cfg:
        MIXED_SET_G_CARDS[set_code] = set(cfg["include"])
    elif "all_except" in cfg:
        end = cfg["set_end"]
        MIXED_SET_G_CARDS[set_code] = set(range(1, end + 1)) - set(cfg["all_except"])

DUPLICATE_SKIP_CARDS: dict[str, set[int]] = {
    set_code: set(numbers) for set_code, numbers in _reg_data["duplicate_skip_cards"].items()
}


def is_g_regulation(set_code: str, card_number: int) -> bool:
    """
    Determine if a card is in G regulation format.

    Args:
        set_code: Set code (e.g., 'JTG')
        card_number: Card number

    Returns:
        True if the card is G regulation, False otherwise
    """
    set_code = set_code.upper()

    if set_code in FULL_G_REGULATION_SETS:
        return True

    if set_code in FULL_I_REGULATION_SETS:
        return False

    if set_code in MIXED_SET_G_CARDS:
        return card_number in MIXED_SET_G_CARDS[set_code]

    return False


def is_duplicate_skip(set_code: str, card_number: int) -> bool:
    """
    Determine if a card should be skipped as a duplicate (same card in another set).

    Args:
        set_code: Set code (e.g., 'ASC')
        card_number: Card number

    Returns:
        True if the card is a duplicate and should be skipped
    """
    set_code = set_code.upper()
    if set_code not in DUPLICATE_SKIP_CARDS:
        return False
    return card_number in DUPLICATE_SKIP_CARDS[set_code]


def filter_g_regulation_cards(cards: list, exclude_g: bool = True) -> list:
    """
    Filter out G regulation cards from a list of cards.

    Args:
        cards: List of CardResult objects or tuples of (set_code, card_number)
        exclude_g: If True, exclude G cards. If False, include all cards.

    Returns:
        Filtered list of cards
    """
    if not exclude_g:
        return cards

    filtered = []
    for card in cards:
        if hasattr(card, "set_code") and hasattr(card, "card_number"):
            if not is_g_regulation(card.set_code, card.card_number):
                filtered.append(card)
        elif isinstance(card, tuple) and len(card) >= 2:
            set_code, card_number = card[0], card[1]
            if not is_g_regulation(set_code, card_number):
                filtered.append(card)

    return filtered
