import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from limitless_scraper import LimitlessScraper

SAMPLE_DECKLIST_HTML = """
<html>
<body>
  <h2 class="name">Pikachu ex</h2>
  <table class="data-table striped spacious">
    <tr><th>Deck</th><th>Placement</th><th>Tournament</th></tr>
    <tr>
      <td>Lightning Beatdown by PlayerOne</td>
      <td>1st</td>
      <td><a href="/tournaments/123">City League 09/07</a></td>
    </tr>
    <tr>
      <td><a href="/decklists/456">Thunder Bolts</a> by PlayerTwo</td>
      <td>2nd</td>
      <td><a href="/tournaments/789">Regional 10/14</a></td>
    </tr>
  </table>
</body>
</html>
"""

NO_DECKLIST_HTML = """
<html>
<body>
  <h2 class="name">Unknown Card</h2>
  <p>No decklists found.</p>
</body>
</html>
"""

NO_TABLE_HTML = """
<html>
<body>
  <h2 class="name">Test Card</h2>
</body>
</html>
"""


@pytest.fixture
def scraper(tmp_path):
    config = {
        "sets": {"JTG": {"start": 1, "end": 3, "enabled": True}},
        "cache_settings": {
            "max_decklist_threshold": 7,
            "cache_ttl_days": 7,
            "cache_save_batch_size": 100,
        },
        "filter_settings": {"exclude_g_regulation": True},
        "scraping_settings": {
            "request_delay": 0.001,
            "max_retries": 1,
            "timeout": 5,
            "user_agent": "test-agent",
        },
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config), encoding="utf-8")
    cache_file = tmp_path / "cache.json"
    return LimitlessScraper(config_file=str(config_file), cache_file=str(cache_file))


class TestScraperInit:
    def test_scraper_initializes(self, scraper):
        assert scraper.session.headers["User-Agent"] == "test-agent"

    def test_scraper_session_type(self, scraper):
        assert isinstance(scraper.session, requests.Session)


class TestPageFetching:
    def test_get_page_success(self, scraper):
        mock_response = MagicMock()
        mock_response.content = b"<html><body>OK</body></html>"
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, "get", return_value=mock_response):
            soup = scraper._get_page_with_requests("https://example.com")
            assert soup is not None
            assert soup.body.get_text(strip=True) == "OK"

    def test_get_page_failure_all_retries_exhausted(self, scraper):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.RequestException("fail")

        with patch.object(scraper.session, "get", return_value=mock_response):
            soup = scraper._get_page_with_requests("https://example.com")
            assert soup is None


class TestDecklistExtraction:
    def test_extract_decklists_with_data(self, scraper):
        soup = BeautifulSoup(SAMPLE_DECKLIST_HTML, "html.parser")
        count, decklists = scraper._extract_decklist_data(soup)
        assert count == 2
        assert decklists[0].deck_name == "Lightning Beatdown"
        assert decklists[0].player_name == "PlayerOne"
        assert decklists[0].placement == "1st"

    def test_extract_decklists_urls(self, scraper):
        soup = BeautifulSoup(SAMPLE_DECKLIST_HTML, "html.parser")
        _, decklists = scraper._extract_decklist_data(soup)
        assert "https://limitlesstcg.com/decklists/456" in decklists[1].decklist_url
        assert "https://limitlesstcg.com/tournaments/789" in decklists[1].tournament_url

    def test_extract_decklists_no_table(self, scraper):
        soup = BeautifulSoup(NO_TABLE_HTML, "html.parser")
        count, decklists = scraper._extract_decklist_data(soup)
        assert count == 0
        assert decklists == []

    def test_extract_decklists_empty_table(self, scraper):
        html = """
        <table class="data-table striped spacious">
          <tr><th>Deck</th><th>Placement</th><th>Tournament</th></tr>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        count, decklists = scraper._extract_decklist_data(soup)
        assert count == 0


class TestScrapeCard:
    def test_scrape_card_success(self, scraper):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DECKLIST_HTML.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.scrape_card("JTG", 1)

        assert result.set_code == "JTG"
        assert result.card_number == 1
        assert result.card_name == "Pikachu ex"
        assert result.decklist_count == 2
        assert result.skip_permanent is False
        assert result.error_message is None

    def test_scrape_card_no_decklists(self, scraper):
        mock_response = MagicMock()
        mock_response.content = NO_DECKLIST_HTML.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.scrape_card("JTG", 1)

        assert result.decklist_count == 0
        assert result.skip_permanent is False

    def test_scrape_card_over_threshold(self, scraper):
        html = """
        <html><body>
          <h2 class="name">Popular Card</h2>
          <table class="data-table striped spacious">
            <tr><th>Deck</th><th>Placement</th><th>Tournament</th></tr>
        """
        for i in range(10):
            html += f"""
            <tr>
              <td>Deck {i} by Player {i}</td>
              <td>{i + 1}th</td>
              <td>Tourney 09/07</td>
            </tr>
            """
        html += "</table></body></html>"

        mock_response = MagicMock()
        mock_response.content = html.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, "get", return_value=mock_response):
            result = scraper.scrape_card("JTG", 1)

        assert result.decklist_count == 10
        assert result.skip_permanent is True

    def test_scrape_card_fetch_failure(self, scraper):
        with patch.object(scraper.session, "get") as mock_get:
            mock_get.side_effect = requests.RequestException("Network error")
            result = scraper.scrape_card("JTG", 1)

        assert result.decklist_count == 0
        assert result.error_message is not None
        assert "Network error" in result.error_message or "Failed to fetch" in result.error_message


class TestScrapeSet:
    def test_scrape_set_unknown_set(self, scraper):
        with pytest.raises(ValueError, match="FAKE"):
            scraper.scrape_set("FAKE")

    def test_scrape_set_disabled(self, scraper):
        scraper.config["sets"]["JTG"]["enabled"] = False
        results = scraper.scrape_set("JTG")
        assert results == []

    def test_scrape_set_progress_callback(self, scraper):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DECKLIST_HTML.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        calls = []

        def callback(set_code, card_number, total, processed, status):
            calls.append((set_code, card_number, status))

        with patch.object(scraper.session, "get", return_value=mock_response):
            scraper.scrape_set("JTG", progress_callback=callback)

        assert len(calls) > 0
        assert calls[0][0] == "JTG"


class TestGetCachedResults:
    def test_get_cached_results_empty(self, scraper):
        assert scraper.get_cached_results() == []

    def test_get_cached_results_with_data(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 3,
            "last_checked": "2026-01-01T00:00:00",
            "skip_permanent": False,
            "card_name": "Test Card",
        }
        results = scraper.get_cached_results(filter_zero_results=False)
        assert len(results) == 1
        assert results[0].card_name == "Test Card"

    def test_get_cached_results_filters_zero(self, scraper):
        scraper.cache["cards"]["JTG_1"] = {
            "decklist_count": 0,
            "last_checked": "2026-01-01T00:00:00",
            "skip_permanent": False,
        }
        scraper.cache["cards"]["JTG_2"] = {
            "decklist_count": 3,
            "last_checked": "2026-01-01T00:00:00",
            "skip_permanent": False,
        }
        results = scraper.get_cached_results(filter_zero_results=True)
        assert len(results) == 1
        assert results[0].card_number == 2


class TestScrapeMultipleSets:
    def test_scrape_multiple_sets(self, scraper):
        mock_response = MagicMock()
        mock_response.content = SAMPLE_DECKLIST_HTML.encode("utf-8")
        mock_response.raise_for_status.return_value = None

        with patch.object(scraper.session, "get", return_value=mock_response):
            results = scraper.scrape_multiple_sets(["JTG"])

        assert "JTG" in results
        assert len(results["JTG"]) == 3
