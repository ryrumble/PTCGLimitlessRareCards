"""
Test script for the LimitlessTCG scraper

This script provides basic testing functionality to verify that the scraper
is working correctly and can help with debugging issues.
"""

import sys
import time
from limitless_scraper import LimitlessScraper


def test_scraper_initialization():
    """Test scraper initialization."""
    print("Testing scraper initialization...")
    try:
        scraper = LimitlessScraper()
        print("✓ Scraper initialized successfully")
        return scraper
    except Exception as e:
        print(f"✗ Failed to initialize scraper: {e}")
        return None


def test_config_loading(scraper):
    """Test configuration loading."""
    print("\nTesting configuration loading...")
    try:
        sets = scraper.config['sets']
        print(f"✓ Loaded {len(sets)} sets from configuration")
        
        # Show first few sets
        for i, (set_code, set_data) in enumerate(sets.items()):
            if i >= 3:  # Show only first 3
                break
            print(f"  {set_code}: {set_data['start']}-{set_data['end']}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to load configuration: {e}")
        return False


def test_cache_loading(scraper):
    """Test cache loading."""
    print("\nTesting cache loading...")
    try:
        cache_stats = scraper.get_cache_stats()
        print(f"✓ Cache loaded successfully")
        print(f"  Total cards: {cache_stats['total_cards']}")
        print(f"  Permanent skips: {cache_stats['permanent_skips']}")
        print(f"  Target range: {cache_stats['target_range']}")
        return True
    except Exception as e:
        print(f"✗ Failed to load cache: {e}")
        return False


def test_single_card_scraping(scraper, set_code="JTG", card_number=21):
    """Test scraping a single card."""
    print(f"\nTesting single card scraping ({set_code} {card_number})...")
    try:
        result = scraper.scrape_card(set_code, card_number)
        print(f"✓ Successfully scraped {set_code} {card_number}")
        print(f"  Decklist count: {result.decklist_count}")
        print(f"  Skip permanent: {result.skip_permanent}")
        print(f"  Error message: {result.error_message or 'None'}")
        
        if result.decklists:
            print(f"  Sample decklist: {result.decklists[0].deck_name}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to scrape card: {e}")
        return False


def test_selenium_fallback(scraper):
    """Test Selenium WebDriver initialization."""
    print("\nTesting Selenium WebDriver...")
    try:
        driver = scraper._get_selenium_driver()
        if driver:
            print("✓ Selenium WebDriver initialized successfully")
            scraper._close_selenium_driver()
            return True
        else:
            print("✗ Failed to initialize Selenium WebDriver")
            return False
    except Exception as e:
        print(f"✗ Selenium WebDriver error: {e}")
        return False


def test_set_scraping(scraper, set_code="JTG", max_cards=5):
    """Test scraping a small set."""
    print(f"\nTesting set scraping ({set_code}, max {max_cards} cards)...")
    try:
        # Temporarily modify the set to limit cards
        original_end = scraper.config['sets'][set_code]['end']
        scraper.config['sets'][set_code]['end'] = scraper.config['sets'][set_code]['start'] + max_cards - 1
        
        def progress_callback(set_code, card_number, total_cards, processed_cards, status):
            print(f"  [{processed_cards}/{total_cards}] {set_code} {card_number}: {status}")
        
        results = scraper.scrape_set(set_code, progress_callback)
        
        # Restore original configuration
        scraper.config['sets'][set_code]['end'] = original_end
        
        print(f"✓ Successfully scraped {len(results)} cards from {set_code}")
        
        # Show summary
        target_cards = sum(1 for card in results 
                          if 1 <= card.decklist_count <= scraper.config['cache_settings']['max_decklist_threshold'])
        print(f"  Cards in target range (1-7): {target_cards}")
        
        return True
    except Exception as e:
        print(f"✗ Failed to scrape set: {e}")
        return False


def test_export_functionality(scraper):
    """Test export functionality."""
    print("\nTesting export functionality...")
    try:
        results = scraper.get_cached_results(filter_zero_results=False)
        if results:
            print(f"✓ Found {len(results)} results to export")
            
            # Test JSON export
            import json
            data = []
            for result in results[:3]:  # Just first 3 for testing
                data.append({
                    'set_code': result.set_code,
                    'card_number': result.card_number,
                    'decklist_count': result.decklist_count,
                    'last_checked': result.last_checked.isoformat(),
                    'skip_permanent': result.skip_permanent
                })
            
            json_output = json.dumps(data, indent=2)
            print(f"✓ JSON export test successful ({len(json_output)} characters)")
            return True
        else:
            print("⚠ No results to export (run scraping first)")
            return True
    except Exception as e:
        print(f"✗ Export test failed: {e}")
        return False


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("           LimitlessTCG Scraper Test Suite")
    print("=" * 60)
    
    # Test initialization
    scraper = test_scraper_initialization()
    if not scraper:
        print("\nCannot continue without scraper initialization.")
        return False
    
    # Run tests
    tests = [
        ("Configuration Loading", lambda: test_config_loading(scraper)),
        ("Cache Loading", lambda: test_cache_loading(scraper)),
        ("Selenium WebDriver", lambda: test_selenium_fallback(scraper)),
        ("Single Card Scraping", lambda: test_single_card_scraping(scraper)),
        ("Export Functionality", lambda: test_export_functionality(scraper)),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! The scraper is working correctly.")
    else:
        print("⚠ Some tests failed. Check the output above for details.")
    
    return passed == total


def interactive_test():
    """Interactive test mode."""
    print("=" * 60)
    print("           Interactive Test Mode")
    print("=" * 60)
    
    scraper = test_scraper_initialization()
    if not scraper:
        return
    
    while True:
        print("\nAvailable tests:")
        print("1. Test single card scraping")
        print("2. Test set scraping (small)")
        print("3. Show cache statistics")
        print("4. Show configuration")
        print("5. Clear cache")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            set_code = input("Enter set code (default: JTG): ").strip().upper() or "JTG"
            try:
                card_number = int(input("Enter card number (default: 21): ").strip() or "21")
                test_single_card_scraping(scraper, set_code, card_number)
            except ValueError:
                print("Invalid card number")
        
        elif choice == "2":
            set_code = input("Enter set code (default: JTG): ").strip().upper() or "JTG"
            try:
                max_cards = int(input("Enter max cards to test (default: 3): ").strip() or "3")
                test_set_scraping(scraper, set_code, max_cards)
            except ValueError:
                print("Invalid number")
        
        elif choice == "3":
            stats = scraper.get_cache_stats()
            print(f"\nCache Statistics:")
            print(f"  Total cards: {stats['total_cards']}")
            print(f"  Permanent skips: {stats['permanent_skips']}")
            print(f"  Zero results: {stats['zero_results']}")
            print(f"  Target range: {stats['target_range']}")
            if stats['last_search_date']:
                from datetime import datetime
                last_search = datetime.fromisoformat(stats['last_search_date'])
                print(f"  Last search: {last_search.strftime('%Y-%m-%d %H:%M:%S')}")
        
        elif choice == "4":
            print(f"\nConfiguration:")
            print(f"  Sets configured: {len(scraper.config['sets'])}")
            print(f"  Max decklist threshold: {scraper.config['cache_settings']['max_decklist_threshold']}")
            print(f"  Request delay: {scraper.config['scraping_settings']['request_delay']}s")
        
        elif choice == "5":
            confirm = input("Are you sure you want to clear the cache? (y/N): ").strip().lower()
            if confirm == 'y':
                scraper.clear_cache()
                print("Cache cleared successfully")
        
        elif choice == "6":
            print("Exiting...")
            break
        
        else:
            print("Invalid choice")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_test()
    else:
        run_all_tests() 