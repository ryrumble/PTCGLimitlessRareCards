"""
LimitlessTCG Scraper CLI Application

This module provides a command-line interface for the LimitlessTCG scraper
with various options for scraping, viewing results, and managing configurations.
"""

import argparse
import sys
import json
from datetime import datetime
from typing import List, Dict
import pandas as pd
from limitless_scraper import LimitlessScraper
from regulation_filter import is_g_regulation


def print_banner():
    """Print application banner."""
    print("=" * 60)
    print("           LimitlessTCG Card Scraper CLI")
    print("=" * 60)
    print()


def print_cache_stats(scraper: LimitlessScraper):
    """Print cache statistics."""
    stats = scraper.get_cache_stats()
    
    print("Cache Statistics:")
    print(f"  Total cards cached: {stats['total_cards']}")
    print(f"  Permanent skips (>7 decklists): {stats['permanent_skips']}")
    print(f"  Zero results: {stats['zero_results']}")
    print(f"  Target range (1-7 decklists): {stats['target_range']}")
    
    if stats['last_search_date']:
        last_search = datetime.fromisoformat(stats['last_search_date'])
        print(f"  Last search: {last_search.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("  Last search: Never")
    print()


def list_sets(scraper: LimitlessScraper):
    """List all configured sets."""
    print("Configured Sets:")
    print(f"{'Set Code':<10} {'Start':<8} {'End':<8} {'Enabled':<10}")
    print("-" * 40)
    
    for set_code, set_data in scraper.config['sets'].items():
        enabled = "Yes" if set_data.get('enabled', True) else "No"
        print(f"{set_code:<10} {set_data['start']:<8} {set_data['end']:<8} {enabled:<10}")
    print()


def view_results(scraper: LimitlessScraper, filter_zero: bool = True, 
                filter_g_regulation: bool = None, output_format: str = "table", output_file: str = None):
    """View cached results."""
    if filter_g_regulation is None:
        filter_g_regulation = scraper.config.get('filter_settings', {}).get('exclude_g_regulation', True)
    results = scraper.get_cached_results(filter_zero_results=filter_zero, filter_g_regulation=filter_g_regulation)
    
    if not results:
        print("No cached results found.")
        return
    
    # Sort results
    results.sort(key=lambda x: (x.set_code, x.card_number))
    
    if output_format == "table":
        print("Cached Results:")
        print(f"{'Set':<6} {'Card':<6} {'Count':<6} {'Latest':<10} {'Last Checked':<20}")
        print("-" * 80)
        
        for result in results:
            last_checked = result.last_checked.strftime("%Y-%m-%d %H:%M")
            latest = getattr(result, 'latest_tournament', '') or ""
            print(f"{result.set_code:<6} {result.card_number:<6} {result.decklist_count:<6} "
                  f"{latest:<10} {last_checked:<20}")
    
    elif output_format == "json":
        data = []
        for result in results:
            data.append({
                'set_code': result.set_code,
                'card_number': result.card_number,
                'decklist_count': result.decklist_count,
                'last_checked': result.last_checked.isoformat(),
                'latest_tournament': getattr(result, 'latest_tournament', None)
            })
        
        output = json.dumps(data, indent=2)
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            print(f"Results exported to {output_file}")
        else:
            print(output)
    
    elif output_format == "csv":
        data = []
        for result in results:
            data.append({
                'Set Code': result.set_code,
                'Card Number': result.card_number,
                'Decklist Count': result.decklist_count,
                'Last Checked': result.last_checked,
                'Skip Permanent': result.skip_permanent
            })
        
        df = pd.DataFrame(data)
        if output_file:
            df.to_csv(output_file, index=False)
            print(f"Results exported to {output_file}")
        else:
            print(df.to_csv(index=False))
    
    elif output_format == "excel":
        data = []
        for result in results:
            data.append({
                'Set Code': result.set_code,
                'Card Number': result.card_number,
                'Decklist Count': result.decklist_count,
                'Last Checked': result.last_checked,
                'Skip Permanent': result.skip_permanent
            })
        
        df = pd.DataFrame(data)
        if output_file:
            df.to_excel(output_file, index=False)
            print(f"Results exported to {output_file}")
        else:
            print("Excel format requires an output file. Use --output-file option.")
            return
    
    print(f"\nTotal results: {len(results)}")
    
    # Show target range summary
    target_results = [r for r in results if 1 <= r.decklist_count <= scraper.config['cache_settings']['max_decklist_threshold']]
    print(f"Cards in target range (1-7 decklists): {len(target_results)}")


def scrape_sets(scraper: LimitlessScraper, set_codes: List[str], verbose: bool = False):
    """Scrape specified sets."""
    print(f"Starting scrape for sets: {', '.join(set_codes)}")
    print()
    
    def progress_callback(set_code, card_number, total_cards, processed_cards, status):
        if verbose:
            if total_cards > 0:
                progress = (processed_cards / total_cards) * 100
                print(f"[{progress:5.1f}%] {set_code} {card_number}: {status}")
            else:
                print(f"{set_code} {card_number}: {status}")
        else:
            # Simple progress indicator
            if processed_cards % 10 == 0 or processed_cards == total_cards:
                print(f"Processed {processed_cards}/{total_cards} cards in {set_code}")
    
    try:
        results = scraper.scrape_multiple_sets(set_codes, progress_callback)
        
        # Print summary
        print("\nScraping completed!")
        print("Summary:")
        
        total_cards = 0
        target_cards = 0
        
        for set_code, set_results in results.items():
            set_total = len(set_results)
            set_target = sum(1 for card in set_results 
                           if 1 <= card.decklist_count <= scraper.config['cache_settings']['max_decklist_threshold'])
            
            print(f"  {set_code}: {set_total} cards processed, {set_target} in target range")
            total_cards += set_total
            target_cards += set_target
        
        print(f"\nTotal: {total_cards} cards processed, {target_cards} in target range")
        
    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
    except Exception as e:
        print(f"\nError during scraping: {e}")
        sys.exit(1)


def manage_sets(scraper: LimitlessScraper, action: str, set_code: str = None, 
                start: int = None, end: int = None, enabled: bool = True):
    """Manage set configurations."""
    if action == "list":
        list_sets(scraper)
        return
    
    elif action == "add":
        if not all([set_code, start, end]):
            print("Error: set_code, start, and end are required for adding a set.")
            return
        
        if set_code in scraper.config['sets']:
            print(f"Error: Set {set_code} already exists.")
            return
        
        scraper.config['sets'][set_code] = {
            'start': start,
            'end': end,
            'enabled': enabled,
            'regulation': '',
            'skip_g_regulation_cards': True,
            'duplicate_skip_numbers': []
        }
        print(f"Added set {set_code} ({start}-{end})")
    
    elif action == "edit":
        if not set_code or set_code not in scraper.config['sets']:
            print(f"Error: Set {set_code} not found.")
            return
        
        if start is not None:
            scraper.config['sets'][set_code]['start'] = start
        if end is not None:
            scraper.config['sets'][set_code]['end'] = end
        if enabled is not None:
            scraper.config['sets'][set_code]['enabled'] = enabled
        
        print(f"Updated set {set_code}")
    
    elif action == "remove":
        if not set_code or set_code not in scraper.config['sets']:
            print(f"Error: Set {set_code} not found.")
            return
        
        del scraper.config['sets'][set_code]
        print(f"Removed set {set_code}")
    
    # Save configuration
    with open(scraper.config_file, 'w') as f:
        json.dump(scraper.config, f, indent=2)


def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(
        description="LimitlessTCG Card Scraper CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View cache statistics
  python cli_app.py stats
  
  # List configured sets
  python cli_app.py sets list
  
  # View cached results
  python cli_app.py view
  
  # Export results to CSV
  python cli_app.py view --format csv --output-file results.csv
  
  # Scrape specific sets
  python cli_app.py scrape JTG SVI
  
  # Scrape with verbose output
  python cli_app.py scrape JTG --verbose
  
  # Add a new set
  python cli_app.py sets add --set-code NEW --start 1 --end 100
  
  # Edit an existing set
  python cli_app.py sets edit --set-code JTG --end 200
  
  # Clear cache
  python cli_app.py cache clear
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show cache statistics')
    
    # View command
    view_parser = subparsers.add_parser('view', help='View cached results')
    view_parser.add_argument('--format', choices=['table', 'json', 'csv', 'excel'], 
                           default='table', help='Output format')
    view_parser.add_argument('--output-file', help='Output file path')
    view_parser.add_argument('--include-zero', action='store_true', 
                           help='Include cards with 0 decklists')
    view_parser.add_argument('--include-g-regulation', action='store_true',
                           help='Include G regulation cards')
    
    # Scrape command
    scrape_parser = subparsers.add_parser('scrape', help='Scrape card sets')
    scrape_parser.add_argument('sets', nargs='+', help='Set codes to scrape')
    scrape_parser.add_argument('--verbose', '-v', action='store_true', 
                             help='Verbose output')
    
    # Sets command
    sets_parser = subparsers.add_parser('sets', help='Manage set configurations')
    sets_subparsers = sets_parser.add_subparsers(dest='sets_action', help='Set actions')
    
    sets_list_parser = sets_subparsers.add_parser('list', help='List all sets')
    
    sets_add_parser = sets_subparsers.add_parser('add', help='Add a new set')
    sets_add_parser.add_argument('--set-code', required=True, help='Set code')
    sets_add_parser.add_argument('--start', type=int, required=True, help='Start card number')
    sets_add_parser.add_argument('--end', type=int, required=True, help='End card number')
    sets_add_parser.add_argument('--disabled', action='store_true', help='Disable the set')
    
    sets_edit_parser = sets_subparsers.add_parser('edit', help='Edit an existing set')
    sets_edit_parser.add_argument('--set-code', required=True, help='Set code')
    sets_edit_parser.add_argument('--start', type=int, help='Start card number')
    sets_edit_parser.add_argument('--end', type=int, help='End card number')
    sets_edit_parser.add_argument('--enable', action='store_true', help='Enable the set')
    sets_edit_parser.add_argument('--disable', action='store_true', help='Disable the set')
    
    sets_remove_parser = sets_subparsers.add_parser('remove', help='Remove a set')
    sets_remove_parser.add_argument('--set-code', required=True, help='Set code')
    
    # Cache command
    cache_parser = subparsers.add_parser('cache', help='Manage cache')
    cache_subparsers = cache_parser.add_subparsers(dest='cache_action', help='Cache actions')
    
    cache_clear_parser = cache_subparsers.add_parser('clear', help='Clear all cached data')
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Initialize scraper
    try:
        scraper = LimitlessScraper()
    except Exception as e:
        print(f"Error initializing scraper: {e}")
        sys.exit(1)
    
    # Execute command
    try:
        if args.command == 'stats':
            print_banner()
            print_cache_stats(scraper)
        
        elif args.command == 'view':
            print_banner()
            view_results(scraper, 
                        filter_zero=not args.include_zero,
                        filter_g_regulation=not args.include_g_regulation,
                        output_format=args.format,
                        output_file=args.output_file)
        
        elif args.command == 'scrape':
            print_banner()
            scrape_sets(scraper, args.sets, verbose=args.verbose)
        
        elif args.command == 'sets':
            if args.sets_action == 'list':
                print_banner()
                list_sets(scraper)
            elif args.sets_action == 'add':
                enabled = not args.disabled
                manage_sets(scraper, 'add', args.set_code, args.start, args.end, enabled)
            elif args.sets_action == 'edit':
                enabled = None
                if args.enable:
                    enabled = True
                elif args.disable:
                    enabled = False
                manage_sets(scraper, 'edit', args.set_code, args.start, args.end, enabled)
            elif args.sets_action == 'remove':
                manage_sets(scraper, 'remove', args.set_code)
            else:
                sets_parser.print_help()
        
        elif args.command == 'cache':
            if args.cache_action == 'clear':
                scraper.clear_cache()
                print("Cache cleared successfully.")
            else:
                cache_parser.print_help()
    
    except KeyboardInterrupt:
        print("\nOperation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 