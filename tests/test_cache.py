import json
from datetime import datetime, timedelta

import pytest

from limitless_scraper import LimitlessScraper


@pytest.fixture
def scraper(tmp_path):
    """Create a scraper with isolated config/cache in a temp directory."""
    config = {
        "sets": {
            "JTG": {"start": 1, "end": 5, "enabled": True},
        },
        "cache_settings": {
            "max_decklist_threshold": 7,
            "cache_ttl_days": 7,
            "cache_save_batch_size": 25,
        },
        "filter_settings": {"exclude_g_regulation": True},
        "scraping_settings": {
            "request_delay": 0.01,
            "max_retries": 1,
            "timeout": 5,
            "user_agent": "test-agent",
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    cache_file = tmp_path / "cache.json"
    return LimitlessScraper(config_file=str(config_file), cache_file=str(cache_file))


class TestCacheOperations:
    def test_initial_cache_is_empty(self, scraper):
        assert scraper.cache["cards"] == {}
        assert scraper.cache["last_search_date"] is None

    def test_clear_cache(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {"decklist_count": 5}
        scraper.clear_cache()
        assert scraper.cache["cards"] == {}
        assert scraper.cache["last_search_date"] is None

    def test_cache_stats_empty(self, scraper):
        stats = scraper.get_cache_stats()
        assert stats["total_cards"] == 0
        assert stats["permanent_skips"] == 0
        assert stats["zero_results"] == 0
        assert stats["target_range"] == 0

    def test_cache_stats_with_data(self, scraper):
        scraper.cache["cards"] = {
            "JTG_1": {"decklist_count": 0, "skip_permanent": False, "last_checked": datetime.now().isoformat()},
            "JTG_2": {"decklist_count": 5, "skip_permanent": False, "last_checked": datetime.now().isoformat()},
            "JTG_3": {"decklist_count": 10, "skip_permanent": True, "last_checked": datetime.now().isoformat()},
        }
        stats = scraper.get_cache_stats()
        assert stats["total_cards"] == 3
        assert stats["permanent_skips"] == 1
        assert stats["zero_results"] == 1
        assert stats["target_range"] == 1

    def test_cache_persistence(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {"decklist_count": 3, "skip_permanent": False}
        scraper._save_cache(force=True)
        scraper.cache = None
        scraper.cache = scraper._load_cache()
        assert "JTG_1" in scraper.cache["cards"]
        assert scraper.cache["cards"]["JTG_1"]["decklist_count"] == 3


class TestCacheSkipLogic:
    def test_skip_card_not_in_cache(self, scraper):
        assert scraper._should_skip_card("JTG", 1) is False

    def test_skip_card_permanent(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 10,
            "skip_permanent": True,
            "last_checked": datetime.now().isoformat(),
        }
        assert scraper._should_skip_card("JTG", 1) is True

    def test_skip_card_permanent_ttl_expired(self, scraper):
        old_date = (datetime.now() - timedelta(days=14)).isoformat()
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 10,
            "skip_permanent": True,
            "last_checked": old_date,
        }
        assert scraper._should_skip_card("JTG", 1) is False

    def test_skip_card_non_permanent_recent(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 3,
            "skip_permanent": False,
            "last_checked": datetime.now().isoformat(),
        }
        assert scraper._should_skip_card("JTG", 1) is True

    def test_skip_card_non_permanent_old(self, scraper):
        old_date = (datetime.now() - timedelta(days=14)).isoformat()
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 3,
            "skip_permanent": False,
            "last_checked": old_date,
        }
        assert scraper._should_skip_card("JTG", 1) is False

    def test_skip_card_zero_decklists_recent(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 0,
            "skip_permanent": False,
            "last_checked": datetime.now().isoformat(),
        }
        assert scraper._should_skip_card("JTG", 1) is True

    def test_skip_card_no_last_checked(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 3,
            "skip_permanent": False,
        }
        assert scraper._should_skip_card("JTG", 1) is False

    def test_duplicate_skip_from_code(self, scraper):
        assert scraper._should_skip_duplicate("ASC", 16) is True

    def test_duplicate_skip_from_config(self, scraper):
        scraper.config["sets"]["JTG"]["duplicate_skip_numbers"] = [99]
        assert scraper._should_skip_duplicate("JTG", 99) is True

    def test_not_duplicate(self, scraper):
        assert scraper._should_skip_duplicate("JTG", 1) is False

    def test_public_wrappers(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 10,
            "skip_permanent": True,
            "last_checked": datetime.now().isoformat(),
        }
        assert scraper.should_skip_card("JTG", 1) is True
        assert scraper.should_skip_duplicate_card("ASC", 16) is True
        assert scraper.should_skip_g_regulation_card("SVI", 1) is True
        assert scraper.should_skip_g_regulation_card("JTG", 1) is False


class TestAtomicCacheSave:
    def test_atomic_write_creates_file(self, scraper, tmp_path):
        cache_file = tmp_path / "cache.json"
        scraper.cache_file = str(cache_file)
        scraper.cache["cards"]["JTG_1"] = {"decklist_count": 1}
        scraper._save_cache(force=True)
        assert cache_file.exists()
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        assert "JTG_1" in data["cards"]

    def test_atomic_write_no_tmp_left_behind(self, scraper, tmp_path):
        cache_file = tmp_path / "cache.json"
        scraper.cache_file = str(cache_file)
        scraper._save_cache(force=True)
        assert not (tmp_path / "cache.json.tmp").exists()

    def test_corrupted_cache_backup(self, scraper, tmp_path):
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("invalid json{", encoding="utf-8")
        scraper.cache_file = str(cache_file)
        cache = scraper._load_cache()
        assert cache["cards"] == {}
        assert cache["last_search_date"] is None
        assert (tmp_path / "cache.json.bak").exists()


class TestBatchSave:
    def test_batch_save_does_not_write_until_threshold(self, scraper, tmp_path):
        cache_file = tmp_path / "cache.json"
        scraper.cache_file = str(cache_file)
        scraper.config["cache_settings"]["cache_save_batch_size"] = 10
        scraper._cache_save_counter = 0
        for i in range(9):
            scraper._save_cache()
            assert scraper._cache_save_counter == i + 1
        assert not cache_file.exists()

    def test_batch_save_writes_at_threshold(self, scraper, tmp_path):
        cache_file = tmp_path / "cache.json"
        scraper.cache_file = str(cache_file)
        scraper.config["cache_settings"]["cache_save_batch_size"] = 5
        scraper._cache_save_counter = 0
        for i in range(4):
            scraper._save_cache()
        assert scraper._cache_save_counter == 4
        scraper._save_cache()
        assert cache_file.exists()
        assert scraper._cache_save_counter == 0

    def test_force_write_bypasses_batch(self, scraper, tmp_path):
        cache_file = tmp_path / "cache.json"
        scraper.cache_file = str(cache_file)
        scraper._save_cache(force=True)
        assert cache_file.exists()
