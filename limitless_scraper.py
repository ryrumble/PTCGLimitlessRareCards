"""
LimitlessTCG Web Scraper

This module contains the core scraping logic for crawling LimitlessTCG card pages
and extracting decklist information with intelligent caching.
"""

import json
import logging
import logging.handlers
import os
import re
import shutil
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from regulation_filter import is_duplicate_skip, is_g_regulation

logger = logging.getLogger(__name__)


@dataclass
class DecklistEntry:
    """Data class for storing decklist entry information."""

    deck_name: str
    player_name: str
    placement: str
    tournament_name: str
    decklist_url: str
    # Optional: direct link to the tournament page (used to derive year)
    tournament_url: str = ""


@dataclass
class CardResult:
    """Data class for storing card scraping results."""

    set_code: str
    card_number: int
    decklist_count: int
    decklists: list[DecklistEntry]
    last_checked: datetime
    skip_permanent: bool
    card_name: str | None = "Unknown Card"
    latest_tournament: str | None = None  # e.g., '2025-09-07' or '09/07'
    error_message: str | None = None


class LimitlessScraper:
    """
    Main scraper class for crawling LimitlessTCG card pages.

    Handles intelligent caching and rate limiting.
    """

    def __init__(self, config_file: str = "config.json", cache_file: str = "cache.json"):
        """
        Initialize the scraper with configuration and cache files.

        Args:
            config_file: Path to configuration JSON file
            cache_file: Path to cache JSON file
        """
        # When frozen by PyInstaller, __file__ points to a temp directory.
        # Use the .exe's directory so config/cache/log live next to the executable.
        if getattr(sys, "frozen", False):
            base_dir = os.path.dirname(sys.executable)
            bundled_dir = sys._MEIPASS  # type: ignore[attr-defined]
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            bundled_dir = None

        self.config_file = config_file if os.path.isabs(config_file) else os.path.join(base_dir, config_file)
        self.cache_file = cache_file if os.path.isabs(cache_file) else os.path.join(base_dir, cache_file)
        self.base_dir = base_dir

        # On first run as .exe, copy the bundled config.json next to the .exe
        # so the GUI can edit and save it locally.
        if bundled_dir and not os.path.exists(self.config_file):
            bundled_config = os.path.join(bundled_dir, config_file)
            if os.path.exists(bundled_config):
                shutil.copy2(bundled_config, self.config_file)

        self.config = self._load_config()
        self._validate_config()
        self.cache = self._load_cache()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.config["scraping_settings"]["user_agent"]})
        self._setup_logging()
        self._cache_save_counter = 0
        self._cache_lock = threading.Lock()
        self._tournament_page_cache: dict[str, str | None] = {}
        # Global rate limiter: ensures at most 1 request per request_delay seconds
        self._rate_lock = threading.Lock()
        self._last_request_time = 0.0

    def _setup_logging(self):
        """Setup logging configuration."""
        if not logger.handlers:
            log_path = os.path.join(self.base_dir, "scraper.log")
            handler_file = logging.handlers.RotatingFileHandler(log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
            handler_stream = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            handler_file.setFormatter(formatter)
            handler_stream.setFormatter(formatter)
            logger.addHandler(handler_file)
            logger.addHandler(handler_stream)
            logger.setLevel(logging.INFO)
        self.logger = logger

    def _load_config(self) -> dict:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_file} not found")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in configuration file: {e}")
            raise

    def _validate_config(self):
        """
        Validate config and fill in defaults for missing keys.
        Mutates self.config in-place.
        """
        defaults = {
            "cache_settings": {
                "max_decklist_threshold": 7,
                "cache_ttl_days": 7,
            },
            "filter_settings": {
                "exclude_g_regulation": True,
            },
            "scraping_settings": {
                "request_delay": 3.0,
                "max_retries": 3,
                "timeout": 30,
                "max_concurrent": 3,
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            },
        }

        for section, section_defaults in defaults.items():
            if section not in self.config:
                self.config[section] = {}
            for key, value in section_defaults.items():  # type: ignore[attr-defined]
                if key not in self.config[section]:
                    self.config[section][key] = value

        # Ensure 'sets' exists and each set has required fields
        if "sets" not in self.config:
            self.config["sets"] = {}
        for set_code, set_data in list(self.config["sets"].items()):
            if "start" not in set_data or "end" not in set_data:
                logger.warning(f"Set {set_code} missing start/end, removing")
                del self.config["sets"][set_code]
                continue
            set_data.setdefault("enabled", True)
            set_data.setdefault("regulation", "")
            set_data.setdefault("skip_g_regulation_cards", True)
            set_data.setdefault("duplicate_skip_numbers", [])

    def _load_cache(self) -> dict:
        """Load cache from JSON file."""
        try:
            with open(self.cache_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {"last_search_date": None, "cards": {}}
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in cache file: {e}")
            # Back up corrupted file before returning empty cache
            backup_path = self.cache_file + ".bak"
            try:
                shutil.copy2(self.cache_file, backup_path)
                self.logger.info(f"Corrupted cache backed up to {backup_path}")
            except Exception as backup_err:
                self.logger.warning(f"Failed to back up corrupted cache: {backup_err}")
            return {"last_search_date": None, "cards": {}}

    def _save_cache(self, force=False):
        """
        Save cache to JSON file with atomic write and batch tracking.

        Args:
            force: If True, write immediately. Otherwise, batch until threshold.
        """
        with self._cache_lock:
            self._cache_save_counter += 1
            batch_size = self.config.get("cache_settings", {}).get("cache_save_batch_size", 25)
            if not force and self._cache_save_counter < batch_size:
                return
            self._cache_save_counter = 0

            tmp_file = self.cache_file + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(self.cache, f, indent=2, default=str)
                os.replace(tmp_file, self.cache_file)
            except Exception as e:
                self.logger.error(f"Failed to save cache: {e}")
                try:
                    if os.path.exists(tmp_file):
                        os.remove(tmp_file)
                except Exception:
                    logger.warning(f"Failed to clean up temp file: {tmp_file}")

    def _get_page_with_requests(self, url: str) -> BeautifulSoup | None:
        """
        Fetch page using requests library.

        Args:
            url: URL to fetch

        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(self.config["scraping_settings"]["max_retries"]):
            try:
                response = self.session.get(url, timeout=self.config["scraping_settings"]["timeout"])

                # Handle 429 Too Many Requests with Retry-After
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    if retry_after and retry_after.isdigit():
                        wait = int(retry_after)
                    else:
                        wait = 2**attempt
                    self.logger.warning(f"Rate limited (429) for {url}, waiting {wait}s")
                    time.sleep(wait)
                    continue

                response.raise_for_status()

                soup = BeautifulSoup(response.content, "lxml")

                return soup

            except requests.RequestException as e:
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config["scraping_settings"]["max_retries"] - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                else:
                    self.logger.error(f"All request attempts failed for {url}: {e}")

        return None

    def _extract_decklist_data(self, soup: BeautifulSoup) -> tuple[int, list[DecklistEntry]]:
        """
        Extract decklist data from BeautifulSoup object.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Tuple of (decklist_count, list_of_decklist_entries)
        """
        table = soup.find("table", class_="data-table striped spacious")
        if not table:
            return 0, []

        rows = table.find_all("tr")  # type: ignore[attr-defined]
        if len(rows) <= 1:  # Only header or empty
            return 0, []

        decklists = []
        # Skip header row
        for row in rows[1:]:
            try:
                cells = row.find_all("td")
                if len(cells) >= 3:
                    deck_player = cells[0].get_text(strip=True)
                    placement = cells[1].get_text(strip=True)
                    tournament_name = cells[2].get_text(strip=True)

                    # Split deck name and player name
                    parts = deck_player.split("by")
                    if len(parts) == 2:
                        deck_name = parts[0].strip()
                        player_name = parts[1].strip()
                    else:
                        deck_name = deck_player
                        player_name = "Unknown"

                    deck_name = deck_name.strip()

                    # Extract decklist URL
                    decklist_link = cells[0].find("a")
                    if decklist_link:
                        decklist_url = decklist_link["href"]
                        if decklist_url and not decklist_url.startswith("http"):
                            decklist_url = f"https://limitlesstcg.com{decklist_url}"
                    else:
                        decklist_url = ""

                    # Extract tournament URL if available (third column)
                    tournament_link = cells[2].find("a")
                    if tournament_link:
                        tournament_url = tournament_link.get("href", "")
                        if tournament_url and not tournament_url.startswith("http"):
                            tournament_url = f"https://limitlesstcg.com{tournament_url}"
                    else:
                        tournament_url = ""

                    decklists.append(
                        DecklistEntry(
                            deck_name=deck_name,
                            player_name=player_name,
                            placement=placement,
                            tournament_name=tournament_name,
                            decklist_url=decklist_url,
                            tournament_url=tournament_url,
                        )
                    )
            except Exception as e:
                self.logger.warning(f"Failed to parse decklist row: {e}")
                continue

        return len(decklists), decklists

    def _should_skip_card(self, set_code: str, card_number: int) -> bool:
        """
        Check if a card should be skipped based on cache.

        Args:
            set_code: Set code (e.g., 'JTG')
            card_number: Card number

        Returns:
            True if card should be skipped
        """
        card_key = f"{set_code}_{card_number}"
        if card_key not in self.cache["cards"]:
            return False

        card_data = self.cache["cards"][card_key]
        ttl_days = self.config.get("cache_settings", {}).get("cache_ttl_days", 30)

        # If permanently skipped, respect TTL before re-checking
        if card_data.get("skip_permanent", False):
            last_checked = card_data.get("last_checked")
            if last_checked:
                age = datetime.now() - datetime.fromisoformat(last_checked)
                if age > timedelta(days=ttl_days):
                    return False  # TTL expired, re-check
            return True  # TTL still valid, skip

        # For non-permanent entries (0 or 1-7 decklists), use a shorter TTL
        short_ttl = max(1, ttl_days // 2)
        last_checked = card_data.get("last_checked")
        if last_checked:
            age = datetime.now() - datetime.fromisoformat(last_checked)
            if age <= timedelta(days=short_ttl):
                return True  # Recently checked, skip

        return False

    def _should_skip_g_regulation(self, set_code: str, card_number: int) -> bool:
        """
        Check if a card should be skipped because it's G regulation.

        Args:
            set_code: Set code (e.g., 'JTG')
            card_number: Card number

        Returns:
            True if card is G regulation and should be skipped
        """
        filter_g_regulation = self.config.get("filter_settings", {}).get("exclude_g_regulation", True)
        if not filter_g_regulation:
            return False

        set_cfg = self.config.get("sets", {}).get(set_code, {})
        if set_cfg.get("skip_g_regulation_cards", True) is False:
            return False

        return is_g_regulation(set_code, card_number)

    def _should_skip_duplicate(self, set_code: str, card_number: int) -> bool:
        """
        Check if a card should be skipped because it's a duplicate.
        """
        if is_duplicate_skip(set_code, card_number):
            return True
        set_cfg = self.config.get("sets", {}).get(set_code, {})
        skip_nums = set_cfg.get("duplicate_skip_numbers") or []
        return card_number in skip_nums

    def should_skip_duplicate_card(self, set_code: str, card_number: int) -> bool:
        """True if this card is skipped as a duplicate (code + config per set)."""
        return self._should_skip_duplicate(set_code, card_number)

    def should_skip_card(self, set_code: str, card_number: int) -> bool:
        """True if this card should be skipped based on cache."""
        return self._should_skip_card(set_code, card_number)

    def should_skip_g_regulation_card(self, set_code: str, card_number: int) -> bool:
        """True if this card is G regulation and should be skipped."""
        return self._should_skip_g_regulation(set_code, card_number)

    def scrape_card(self, set_code: str, card_number: int) -> CardResult:
        """
        Scrape a single card page.

        Args:
            set_code: Set code (e.g., 'JTG')
            card_number: Card number

        Returns:
            CardResult object with scraping results
        """
        url = f"https://limitlesstcg.com/cards/{set_code}/{card_number}/decklists/jp"
        card_key = f"{set_code}_{card_number}"

        self.logger.info(f"Scraping {set_code} {card_number}: {url}")

        # Try requests first
        soup = self._get_page_with_requests(url)

        if soup is None:
            error_msg = f"Failed to fetch page for {set_code} {card_number}"
            self.logger.error(error_msg)
            return CardResult(
                set_code=set_code,
                card_number=card_number,
                decklist_count=0,
                decklists=[],
                last_checked=datetime.now(),
                skip_permanent=False,
                error_message=error_msg,
            )

        # Extract card name
        try:
            card_name_element = soup.find("h2", class_="name")
            card_name = card_name_element.text.strip() if card_name_element else "Unknown Card"
        except Exception as e:
            card_name = "Unknown Card - Error: " + str(e)

        # Extract decklist data
        decklist_count, decklists = self._extract_decklist_data(soup)

        # Extract latest tournament date based on table order (top row is latest)
        # Optionally append the year by visiting the tournament page link.
        latest_tournament: str | None = None
        if decklists:
            first_entry = decklists[0]
            match = re.search(r"(\d{2})\/(\d{2})", first_entry.tournament_name)
            if match:
                month = int(match.group(1))
                day = int(match.group(2))
                latest_tournament = f"{month:02d}/{day:02d}"

                # Try to fetch year from the tournament page if available (cached)
                try:
                    if first_entry.tournament_url:
                        tournament_year = self._tournament_page_cache.get(first_entry.tournament_url)
                        if tournament_year is None:
                            tournament_soup = self._get_page_with_requests(first_entry.tournament_url)
                            if tournament_soup is not None:
                                page_text = tournament_soup.get_text(" ", strip=True)
                                year_match = re.search(
                                    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\s+(20\d{2})",
                                    page_text,
                                )
                                if not year_match:
                                    year_match = re.search(r"\b(20\d{2})\b", page_text)
                                if year_match:
                                    tournament_year = (
                                        year_match.group(2) if len(year_match.groups()) >= 2 else year_match.group(1)
                                    )
                            self._tournament_page_cache[first_entry.tournament_url] = tournament_year
                        if tournament_year:
                            latest_tournament = f"{latest_tournament}/{tournament_year}"
                except Exception as e:
                    self.logger.warning(f"Failed to fetch tournament year: {e}")

        # Determine if this card should be permanently skipped
        skip_permanent = decklist_count > self.config["cache_settings"]["max_decklist_threshold"]

        # Update cache (thread-safe)
        with self._cache_lock:
            self.cache["cards"][card_key] = {
                "decklist_count": decklist_count,
                "last_checked": datetime.now().isoformat(),
                "skip_permanent": skip_permanent,
                "card_name": card_name,
                "latest_tournament": latest_tournament,
            }

        # Global rate limiting (ensures politeness across concurrent workers)
        self._rate_limit_wait()

        return CardResult(
            set_code=set_code,
            card_number=card_number,
            decklist_count=decklist_count,
            decklists=decklists,
            last_checked=datetime.now(),
            skip_permanent=skip_permanent,
            card_name=card_name,
            latest_tournament=latest_tournament,
        )

    def scrape_set(self, set_code: str, progress_callback=None) -> list[CardResult]:
        """
        Scrape all cards in a set.

        Args:
            set_code: Set code to scrape
            progress_callback: Optional callback function for progress updates

        Returns:
            List of CardResult objects
        """
        if set_code not in self.config["sets"]:
            raise ValueError(f"Set {set_code} not found in configuration")

        set_config = self.config["sets"][set_code]
        if not set_config.get("enabled", True):
            self.logger.info(f"Set {set_code} is disabled, skipping")
            return []

        total_cards = set_config["end"] - set_config["start"] + 1
        processed_cards = 0
        results: list[CardResult] = []
        cards_to_scrape: list[int] = []
        results_lock = threading.Lock()

        # First pass: fast skip checks (sequential)
        for card_number in range(set_config["start"], set_config["end"] + 1):
            if self._should_skip_duplicate(set_code, card_number):
                self.logger.info(f"Skipping {set_code} {card_number} (duplicate)")
                processed_cards += 1
                if progress_callback:
                    progress_callback(set_code, card_number, total_cards, processed_cards, "Skipped (duplicate)")
                continue

            if self._should_skip_g_regulation(set_code, card_number):
                self.logger.info(f"Skipping {set_code} {card_number} (G regulation)")
                processed_cards += 1
                if progress_callback:
                    progress_callback(set_code, card_number, total_cards, processed_cards, "Skipped (G regulation)")
                continue

            if self._should_skip_card(set_code, card_number):
                self.logger.info(f"Skipping {set_code} {card_number} (permanently cached)")
                processed_cards += 1
                if progress_callback:
                    progress_callback(set_code, card_number, total_cards, processed_cards, "Skipped")
                continue

            cards_to_scrape.append(card_number)

        if not cards_to_scrape:
            return results

        # Second pass: scrape remaining cards concurrently
        max_workers = self.config.get("scraping_settings", {}).get("max_concurrent", 3)
        self.logger.info(f"Scraping {len(cards_to_scrape)} cards in {set_code} with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_card = {executor.submit(self.scrape_card, set_code, cn): cn for cn in cards_to_scrape}

            for future in as_completed(future_to_card):
                card_number = future_to_card[future]
                try:
                    result = future.result()
                    with results_lock:
                        results.append(result)
                    processed_cards += 1
                    if progress_callback:
                        progress_callback(
                            set_code,
                            card_number,
                            total_cards,
                            processed_cards,
                            f"Found {result.decklist_count} decklists",
                        )
                except Exception as e:
                    self.logger.error(f"Error scraping {set_code} {card_number}: {e}")
                    processed_cards += 1
                    if progress_callback:
                        progress_callback(set_code, card_number, total_cards, processed_cards, f"Error: {e}")

        return results

    def scrape_multiple_sets(self, set_codes: list[str], progress_callback=None) -> dict[str, list[CardResult]]:
        """
        Scrape multiple sets.

        Args:
            set_codes: List of set codes to scrape
            progress_callback: Optional callback function for progress updates

        Returns:
            Dictionary mapping set codes to lists of CardResult objects
        """
        all_results = {}

        for set_code in set_codes:
            if progress_callback:
                progress_callback(set_code, 0, 0, 0, f"Starting set {set_code}")

            try:
                results = self.scrape_set(set_code, progress_callback)
                all_results[set_code] = results
            except Exception as e:
                self.logger.error(f"Error scraping set {set_code}: {e}")
                all_results[set_code] = []

        # Update last search date
        self.cache["last_search_date"] = datetime.now().isoformat()
        self._save_cache(force=True)

        return all_results

    def get_cached_results(
        self, filter_zero_results: bool = True, filter_g_regulation: bool | None = None
    ) -> list[CardResult]:
        """
        Get all cached results.

        Args:
            filter_zero_results: Whether to filter out cards with 0 decklists
            filter_g_regulation: Whether to filter out G regulation cards.
                                If None, uses config setting.

        Returns:
            List of CardResult objects
        """
        # Use config setting if not explicitly provided
        if filter_g_regulation is None:
            filter_g_regulation = self.config.get("filter_settings", {}).get("exclude_g_regulation", True)

        results = []

        for card_key, card_data in self.cache["cards"].items():
            set_code, card_number_str = card_key.split("_", 1)
            card_number = int(card_number_str)

            if filter_g_regulation:
                set_cfg = self.config.get("sets", {}).get(set_code, {})
                if set_cfg.get("skip_g_regulation_cards", True) and is_g_regulation(set_code, card_number):
                    continue

            if self._should_skip_duplicate(set_code, card_number):
                continue

            # Filter out zero results if requested
            if filter_zero_results and card_data["decklist_count"] == 0:
                continue

            # Parse last checked date
            last_checked = datetime.fromisoformat(card_data["last_checked"])

            results.append(
                CardResult(
                    set_code=set_code,
                    card_number=card_number,
                    decklist_count=card_data["decklist_count"],
                    decklists=[],  # Decklists not stored in cache
                    last_checked=last_checked,
                    skip_permanent=card_data.get("skip_permanent", False),
                    card_name=card_data.get("card_name", "Unknown Card"),
                    latest_tournament=card_data.get("latest_tournament"),
                )
            )

        return results

    def _rate_limit_wait(self):
        """Global rate limiter: blocks until at least request_delay seconds
        have passed since the last request across ALL threads."""
        delay = self.config.get("scraping_settings", {}).get("request_delay", 3.0)
        with self._rate_lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < delay:
                time.sleep(delay - elapsed)
            self._last_request_time = time.time()

    def clear_cache(self):
        """Clear all cached data."""
        self.cache = {"last_search_date": None, "cards": {}}
        self._save_cache(force=True)
        self.logger.info("Cache cleared")

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        total_cards = len(self.cache["cards"])
        permanent_skips = sum(1 for card in self.cache["cards"].values() if card.get("skip_permanent", False))
        zero_results = sum(1 for card in self.cache["cards"].values() if card["decklist_count"] == 0)
        target_range = sum(
            1
            for card in self.cache["cards"].values()
            if 1 <= card["decklist_count"] <= self.config["cache_settings"]["max_decklist_threshold"]
        )

        return {
            "total_cards": total_cards,
            "permanent_skips": permanent_skips,
            "zero_results": zero_results,
            "target_range": target_range,
            "last_search_date": self.cache.get("last_search_date"),
        }
