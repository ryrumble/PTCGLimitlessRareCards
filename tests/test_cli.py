import sys
from unittest.mock import patch

import pytest

from cli_app import main


def _make_card_result(set_code="JTG", card_number=1, decklist_count=3):
    """Create a minimal CardResult-like object for mocking."""
    from datetime import datetime

    class FakeResult:
        def __init__(self, set_code, card_number, decklist_count):
            self.set_code = set_code
            self.card_number = card_number
            self.decklist_count = decklist_count
            self.card_name = "Test Card"
            self.last_checked = datetime(2026, 1, 1)
            self.skip_permanent = False
            self.latest_tournament = "01/01/2026"
            self.decklists = []
            self.error_message = None

    return FakeResult(set_code, card_number, decklist_count)


@pytest.fixture
def mock_scraper():
    """Patch LimitlessScraper to avoid file I/O during CLI tests."""
    with patch("cli_app.LimitlessScraper") as mock:
        instance = mock.return_value
        instance.config = {
            "sets": {"JTG": {"start": 1, "end": 5, "enabled": True}},
            "cache_settings": {"max_decklist_threshold": 7},
            "filter_settings": {"exclude_g_regulation": True},
            "scraping_settings": {"request_delay": 0.01},
        }
        instance.cache = {"last_search_date": None, "cards": {}}
        instance.get_cache_stats.return_value = {
            "total_cards": 10,
            "permanent_skips": 2,
            "zero_results": 3,
            "target_range": 5,
            "last_search_date": None,
        }
        instance.get_cached_results.return_value = [
            _make_card_result("JTG", 1, 3),
            _make_card_result("JTG", 2, 0),
        ]
        instance.should_skip_duplicate_card.return_value = False
        instance.clear_cache.return_value = None
        yield


def run_main(argv):
    """Run CLI main with given argv and capture SystemExit."""
    with patch.object(sys, "argv", ["cli_app.py"] + argv):
        try:
            main()
        except SystemExit as e:
            return e.code
    return 0


class TestCliStats:
    def test_stats_command(self, mock_scraper, capsys):
        code = run_main(["stats"])
        output = capsys.readouterr().out
        assert "Cache Statistics" in output
        assert code == 0


class TestCliView:
    def test_view_default(self, mock_scraper, capsys):
        code = run_main(["view"])
        assert code == 0

    def test_view_json(self, mock_scraper, capsys):
        code = run_main(["view", "--format", "json"])
        assert code == 0

    def test_view_with_output_file(self, mock_scraper, tmp_path, capsys):
        out = tmp_path / "out.json"
        code = run_main(["view", "--format", "json", "--output-file", str(out)])
        assert code == 0
        assert out.exists()


class TestCliScrape:
    def test_scrape_single_set(self, mock_scraper, capsys):
        code = run_main(["scrape", "JTG"])
        assert code == 0

    def test_scrape_verbose(self, mock_scraper, capsys):
        code = run_main(["scrape", "JTG", "--verbose"])
        assert code == 0


class TestCliSets:
    def test_sets_list(self, mock_scraper, capsys):
        code = run_main(["sets", "list"])
        assert code == 0

    def test_sets_add(self, mock_scraper, capsys):
        code = run_main(["sets", "add", "--set-code", "NEW", "--start", "1", "--end", "10"])
        assert code == 0

    def test_sets_edit(self, mock_scraper, capsys):
        code = run_main(["sets", "edit", "--set-code", "JTG", "--end", "10"])
        assert code == 0

    def test_sets_remove(self, mock_scraper, capsys):
        code = run_main(["sets", "remove", "--set-code", "JTG"])
        assert code == 0


class TestCliCache:
    def test_cache_clear(self, mock_scraper, capsys):
        code = run_main(["cache", "clear"])
        assert code == 0


class TestCliError:
    def test_no_command_shows_help(self, mock_scraper, capsys):
        code = run_main([])
        assert code == 0  # parser.print_help() doesn't sys.exit

    def test_invalid_command(self, mock_scraper, capsys):
        code = run_main(["invalid"])
        assert code == 2  # argparse exits with 2 on unknown command
