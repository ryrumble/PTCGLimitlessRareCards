"""
Regulation Format Filter

This module provides functionality to determine if a card is in G regulation format,
which is used to filter out rotating cards from searches and displays.
"""

from typing import Set


# Sets that are entirely G regulation (all cards are G)
FULL_G_REGULATION_SETS: Set[str] = {
    "SVI", "PAL", "OBF", "MEW", "PAR", "PAF"
}

# Sets that are entirely I regulation (no G cards)
FULL_I_REGULATION_SETS: Set[str] = {
    "WHT", "MEG", "PFL"
}

# Mixed sets with specific G regulation cards
# Format: {set_code: {card_numbers that are G}}
MIXED_SET_G_CARDS: dict[str, Set[int]] = {
    # TWM: only card 161 is H (rest are G, but we track G cards)
    # Actually, all cards except 161 are G, so we'll handle this differently
    "TWM": set(range(1, 161)) | set(range(162, 168)),  # All except 161
    
    # TEF: cards 22, 140, 149 are H (rest are G)
    "TEF": set(range(1, 22)) | set(range(23, 140)) | set(range(141, 149)) | set(range(150, 163)),
    
    # SCR: cards 1, 21, 30, 62, 89 are G (rest are H)
    "SCR": {1, 21, 30, 62, 89},
    
    # PRE: all cards except 13,22,29,31,33,42,49,56,59,106,120,121,122,123,124,125,130 are H
    # So these are G: 13,22,29,31,33,42,49,56,59,106,120,121,122,123,124,125,130
    "PRE": {13, 22, 29, 31, 33, 42, 49, 56, 59, 106, 120, 121, 122, 123, 124, 125, 130},
    
    # JTG: card 155 is G (others are H or I)
    "JTG": {155},
    
    # DRI: card 167 is G (others are H or I)
    "DRI": {167},
    
    # BLK: card 85 is G (card 80 is H, rest are I)
    "BLK": {85},
}

# Cards to skip as duplicates (same card in another set). Format: {set_code: {card_numbers}}
DUPLICATE_SKIP_CARDS: dict[str, Set[int]] = {
    "ASC": {
        16, 17, 18, 19, 23, 24, 26, 32, 33, 36, 37, 38, 39, 40, 44, 45,
        57, 59, 60, 65, 66, 69, 70, 71, 72, 74, 75, 76, 79, 80, 81, 82,
        87, 88, 89, 90, 91, 97, 99, 105, 106, 107, 109, 110, 111, 112, 113,
        123, 124, 125, 126, 128, 129, 133, 136, 137, 142, 154, 158, 159, 160, 161,
        171, 177, 178, 179, 180, 181, 183, 184, 186, 187, 188, 189, 190,
        192, 193, 194, 195, 196, 199, 200, 201, 202, 203, 204, 205, 207, 208, 209, 210, 212, 213,
    },
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
    
    # Check if set is entirely G regulation
    if set_code in FULL_G_REGULATION_SETS:
        return True
    
    # Check if set is entirely I regulation (no G cards)
    if set_code in FULL_I_REGULATION_SETS:
        return False
    
    # Check mixed sets
    if set_code in MIXED_SET_G_CARDS:
        return card_number in MIXED_SET_G_CARDS[set_code]
    
    # For sets not in our mapping, assume not G regulation
    # (This handles sets like SVP, SFA, SSP that weren't mentioned)
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
        if hasattr(card, 'set_code') and hasattr(card, 'card_number'):
            # CardResult object
            if not is_g_regulation(card.set_code, card.card_number):
                filtered.append(card)
        elif isinstance(card, tuple) and len(card) >= 2:
            # Tuple of (set_code, card_number, ...)
            set_code, card_number = card[0], card[1]
            if not is_g_regulation(set_code, card_number):
                filtered.append(card)
    
    return filtered
