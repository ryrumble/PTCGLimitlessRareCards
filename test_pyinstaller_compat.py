"""
Tests for PyInstaller frozen-mode path handling.

Verifies that LimitlessScraper correctly resolves config.json, cache.json,
and scraper.log paths when running as a normal Python script AND when
running as a PyInstaller --onefile bundle.

These tests do NOT make any network requests.
"""

import json
import logging
import os
import shutil
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from limitless_scraper import LimitlessScraper


@pytest.fixture(autouse=True)
def _clear_logger_handlers():
    """Remove all handlers from the module-level logger before each test
    so _setup_logging() re-adds them with the correct base_dir."""
    logger = logging.getLogger("limitless_scraper")
    logger.handlers.clear()
    yield
    logger.handlers.clear()


@pytest.fixture
def project_config():
    """Return the path to the real config.json in the project root."""
    return Path(__file__).parent / "config.json"


@pytest.fixture
def fake_exe_env(tmp_path, project_config):
    """Create a temporary directory structure mimicking a PyInstaller --onefile run.

    Returns (exe_dir, bundled_dir) where:
      - exe_dir is the directory containing the "executable"
      - bundled_dir is sys._MEIPASS (contains bundled read-only files)
    """
    exe_dir = tmp_path / "exe_dir"
    exe_dir.mkdir()

    bundled_dir = tmp_path / "bundled"
    bundled_dir.mkdir()

    # Place config.json in the bundled dir (simulates --add-data)
    shutil.copy2(project_config, bundled_dir / "config.json")

    return exe_dir, bundled_dir


class TestNonFrozenPaths:
    """When running normally (not frozen), paths resolve relative to __file__."""

    def test_config_file_resolves_to_source_dir(self):
        scraper = LimitlessScraper.__new__(LimitlessScraper)
        base_dir = os.path.dirname(os.path.abspath(LimitlessScraper.__module__.replace(".", "/") + ".py"))
        # The module file for limitless_scraper.py
        module_file = sys.modules["limitless_scraper"].__file__
        expected_base = os.path.dirname(module_file)

        config_file = "config.json"
        result = config_file if os.path.isabs(config_file) else os.path.join(expected_base, config_file)
        assert result.endswith("config.json")
        assert expected_base in result

    def test_cache_file_resolves_to_source_dir(self):
        module_file = sys.modules["limitless_scraper"].__file__
        expected_base = os.path.dirname(module_file)

        cache_file = "cache.json"
        result = cache_file if os.path.isabs(cache_file) else os.path.join(expected_base, cache_file)
        assert result.endswith("cache.json")
        assert expected_base in result

    def test_scraper_instantiates_normally(self):
        """Baseline: scraper works without any mocking."""
        scraper = LimitlessScraper()
        assert "sets" in scraper.config
        assert "cards" in scraper.cache


class TestFrozenPaths:
    """When running as a PyInstaller bundle, paths resolve relative to sys.executable."""

    def test_config_file_resolves_to_exe_dir(self, fake_exe_env):
        exe_dir, bundled_dir = fake_exe_env

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            patch.object(sys, "executable", str(exe_dir / "LimitlessTCGScraper.exe"), create=True),
        ):
            scraper = LimitlessScraper()

        expected_config = os.path.join(str(exe_dir), "config.json")
        assert scraper.config_file == expected_config

    def test_cache_file_resolves_to_exe_dir(self, fake_exe_env):
        exe_dir, bundled_dir = fake_exe_env

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            patch.object(sys, "executable", str(exe_dir / "LimitlessTCGScraper.exe"), create=True),
        ):
            scraper = LimitlessScraper()

        expected_cache = os.path.join(str(exe_dir), "cache.json")
        assert scraper.cache_file == expected_cache

    def test_config_copied_from_bundled_on_first_run(self, fake_exe_env):
        exe_dir, bundled_dir = fake_exe_env

        # config.json should NOT exist in exe_dir yet
        assert not (exe_dir / "config.json").exists()

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            patch.object(sys, "executable", str(exe_dir / "LimitlessTCGScraper.exe"), create=True),
        ):
            scraper = LimitlessScraper()

        # config.json should now exist in exe_dir (copied from bundled)
        assert (exe_dir / "config.json").exists()

        # Verify the content matches the bundled original
        original = json.loads((bundled_dir / "config.json").read_text(encoding="utf-8"))
        copied = json.loads((exe_dir / "config.json").read_text(encoding="utf-8"))
        assert original == copied

    def test_config_not_overwritten_if_already_exists(self, fake_exe_env):
        exe_dir, bundled_dir = fake_exe_env

        # Place a valid but different config.json in exe_dir
        modified_config = {
            "sets": {"CUSTOM": {"start": 1, "end": 10, "enabled": True}},
            "cache_settings": {"max_decklist_threshold": 5},
            "scraping_settings": {"request_delay": 2.0, "max_retries": 1, "timeout": 10, "user_agent": "custom-agent"},
        }
        (exe_dir / "config.json").write_text(json.dumps(modified_config), encoding="utf-8")

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            patch.object(sys, "executable", str(exe_dir / "LimitlessTCGScraper.exe"), create=True),
        ):
            scraper = LimitlessScraper()

        # The local config should NOT have been overwritten
        local_config = json.loads((exe_dir / "config.json").read_text(encoding="utf-8"))
        assert local_config == modified_config

    def test_log_file_resolves_to_exe_dir(self, fake_exe_env):
        exe_dir, bundled_dir = fake_exe_env

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            patch.object(sys, "executable", str(exe_dir / "LimitlessTCGScraper.exe"), create=True),
        ):
            scraper = LimitlessScraper()

        expected_log = os.path.join(str(exe_dir), "scraper.log")
        file_handlers = [h for h in scraper.logger.handlers if isinstance(h, logging.FileHandler)]
        assert len(file_handlers) >= 1
        assert file_handlers[0].baseFilename == os.path.abspath(expected_log)


class TestAbsolutePathsUnaffected:
    """If absolute paths are passed in, frozen/unfrozen mode should not change them."""

    def test_absolute_config_path_used_as_is(self, fake_exe_env, tmp_path):
        exe_dir, bundled_dir = fake_exe_env
        custom_config = tmp_path / "custom_config.json"
        custom_config.write_text(
            json.dumps(
                {
                    "sets": {},
                    "cache_settings": {"max_decklist_threshold": 7},
                    "scraping_settings": {"request_delay": 1.0, "max_retries": 3, "timeout": 30, "user_agent": "test"},
                }
            ),
            encoding="utf-8",
        )

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(bundled_dir), create=True),
            patch.object(sys, "executable", str(exe_dir / "LimitlessTCGScraper.exe"), create=True),
        ):
            scraper = LimitlessScraper(config_file=str(custom_config))

        assert scraper.config_file == str(custom_config)
