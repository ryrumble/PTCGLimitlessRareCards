import json

import pytest

from limitless_scraper import LimitlessScraper


def write_config(tmp_path, config_dict):
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_dict), encoding="utf-8")
    cache_file = tmp_path / "cache.json"
    return LimitlessScraper(config_file=str(config_file), cache_file=str(cache_file))


class TestConfigLoading:
    def test_load_valid_config(self, tmp_path):
        config = {
            "sets": {"JTG": {"start": 1, "end": 5, "enabled": True}},
            "cache_settings": {"max_decklist_threshold": 7, "cache_ttl_days": 7},
            "filter_settings": {"exclude_g_regulation": True},
            "scraping_settings": {
                "request_delay": 0.01,
                "max_retries": 1,
                "timeout": 5,
                "user_agent": "test",
            },
        }
        scraper = write_config(tmp_path, config)
        assert len(scraper.config["sets"]) == 1
        assert scraper.config["sets"]["JTG"]["start"] == 1

    def test_missing_config_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            LimitlessScraper(
                config_file=str(tmp_path / "nonexistent.json"),
                cache_file=str(tmp_path / "cache.json"),
            )

    def test_invalid_json_config(self, tmp_path):
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json}", encoding="utf-8")
        cache_file = tmp_path / "cache.json"
        with pytest.raises(json.JSONDecodeError):
            LimitlessScraper(config_file=str(config_file), cache_file=str(cache_file))


class TestConfigDefaults:
    def test_missing_cache_settings_filled(self, tmp_path):
        config = {
            "sets": {},
            "scraping_settings": {"user_agent": "test"},
        }
        scraper = write_config(tmp_path, config)
        assert scraper.config["cache_settings"]["max_decklist_threshold"] == 7
        assert scraper.config["cache_settings"]["cache_ttl_days"] == 7

    def test_missing_filter_settings_filled(self, tmp_path):
        config = {
            "sets": {},
        }
        scraper = write_config(tmp_path, config)
        assert scraper.config["filter_settings"]["exclude_g_regulation"] is True

    def test_missing_scraping_settings_filled(self, tmp_path):
        config = {
            "sets": {},
        }
        scraper = write_config(tmp_path, config)
        assert scraper.config["scraping_settings"]["request_delay"] == 3.0
        assert scraper.config["scraping_settings"]["max_retries"] == 3

    def test_missing_sets_defaults_to_empty(self, tmp_path):
        config = {}
        scraper = write_config(tmp_path, config)
        assert scraper.config["sets"] == {}

    def test_set_missing_fields_filled(self, tmp_path):
        config = {
            "sets": {
                "JTG": {"start": 1, "end": 5},
            },
        }
        scraper = write_config(tmp_path, config)
        assert scraper.config["sets"]["JTG"]["enabled"] is True
        assert scraper.config["sets"]["JTG"]["regulation"] == ""
        assert scraper.config["sets"]["JTG"]["skip_g_regulation_cards"] is True
        assert scraper.config["sets"]["JTG"]["duplicate_skip_numbers"] == []

    def test_invalid_set_removed(self, tmp_path):
        config = {
            "sets": {
                "GOOD": {"start": 1, "end": 5},
                "BAD": {"start": 1},
            },
        }
        scraper = write_config(tmp_path, config)
        assert "GOOD" in scraper.config["sets"]
        assert "BAD" not in scraper.config["sets"]
