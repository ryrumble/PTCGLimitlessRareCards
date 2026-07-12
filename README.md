# LimitlessTCG Card Scraper

A comprehensive Python web scraping application for crawling LimitlessTCG card pages and counting decklist results. The application features intelligent caching, both GUI and CLI interfaces, and is designed to efficiently identify cards with 1-7 decklists (the "sweet spot" for rare card placement analysis).

## Features

### 🎯 Core Functionality
- **Smart Web Scraping**: Crawls LimitlessTCG card pages with intelligent caching
- **Dual Interface**: Both GUI (tkinter) and CLI applications
- **Intelligent Caching**: 
  - Permanent skip for cards with >7 decklists
  - Temporary cache for cards with 0 decklists (re-check in future)
  - Temporary cache for cards with 1-7 decklists (re-check periodically)
- **Set Management**: Add, edit, remove, and configure card sets
- **Export Options**: CSV and Excel export formats

### 🔧 Technical Features
- **Web Scraping**: Requests-based with rate limiting and retry logic
- **Rate Limiting**: Respectful scraping with configurable delays
- **Error Handling**: Comprehensive error handling and logging
- **Threading**: Non-blocking GUI operations during scraping
- **Cross-Platform**: Works on Windows, macOS, and Linux

### 📊 Data Extraction
- Extracts decklist count from "data-table striped spacious" tables
- Identifies cards with 1-7 decklists (target range)
- Handles pages with 0 results gracefully
- Extracts deck name, player name, placement, tournament name, and decklist URL

## Installation

### Quick Start (No Python Required)

If you just want to use the app without installing Python:

1. Download `LimitlessTCGScraper.exe` from the latest [GitHub Release](../../releases)
2. Place it next to a `config.json` file (see below for config)
3. Double-click to run — `cache.json` and `scraper.log` are created automatically in the same directory

**To get a `config.json`:** Either copy one from this repository, or the `.exe` will auto-create a default one on first run if bundled. You can also run the app once from source to generate it, then use that file alongside the `.exe`.

### Prerequisites
- Python 3.7 or higher

### Setup
1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd pkmnOnlineLimitlessRarePlacingCardsJapanTournaments
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**
   ```bash
   python -c "import limitless_scraper; print('Installation successful!')"
   ```

## Quick Start

### GUI Application
```bash
python run_gui.py
```

### CLI Application
```bash
# View cache statistics
python cli_app.py stats

# List configured sets
python cli_app.py sets list

# View cached results
python cli_app.py view
```

## Usage

### GUI Application

The GUI application provides two main modes:

#### View Results Mode
- **Display cached results** without performing new searches
- **Filter options**: Show/hide cards with 0 decklists
  - Hide cards with decklists >= configurable threshold (default 8)
  - Filter by latest tournament month (MM), based on scraped decklist rows
- **Clickable links**: Double-click cards to open LimitlessTCG pages
- **Export functionality**: Export results in CSV or Excel formats
- **Cache management**: Clear cache and view statistics
- **Card Name column**: Shows the Pokémon/card name (persisted in cache)

#### Search Mode
- **Select sets** to scrape from the configured list
- **Real-time progress** tracking with progress bars
- **Live logging** of scraping activities
- **Start/Stop controls** for managing scraping sessions
- **Set management** interface for adding/editing set configurations

### CLI Application

#### View Cache Statistics
```bash
python cli_app.py stats
```

#### View Cached Results
```bash
# View in table format (default)
python cli_app.py view

# Include cards with 0 decklists
python cli_app.py view --include-zero

# Export to CSV
python cli_app.py view --format csv --output-file results.csv

# Export to Excel
python cli_app.py view --format excel --output-file results.xlsx

# Export to JSON
python cli_app.py view --format json --output-file results.json
```

#### Scrape Card Sets
```bash
# Scrape specific sets
python cli_app.py scrape JTG SVI

# Scrape with verbose output
python cli_app.py scrape JTG --verbose

# Scrape multiple sets
python cli_app.py scrape JTG SVI PAL OBF
```

#### Manage Set Configurations
```bash
# List all configured sets
python cli_app.py sets list

# Add a new set
python cli_app.py sets add --set-code NEW --start 1 --end 100

# Edit an existing set
python cli_app.py sets edit --set-code JTG --end 200

# Disable a set
python cli_app.py sets edit --set-code JTG --disable

# Remove a set
python cli_app.py sets remove --set-code OLD
```

#### Cache Management
```bash
# Clear all cached data
python cli_app.py cache clear
```

## Configuration

### Default Sets
The application comes pre-configured with the following Pokemon TCG sets:

| Set Code | Start | End | Description |
|----------|-------|-----|-------------|
| SVP | 1 | 207 | Scarlet & Violet—Paldea Evolved |
| SVI | 1 | 198 | Scarlet & Violet |
| PAL | 1 | 193 | Paldea Evolved |
| OBF | 1 | 197 | Obsidian Flames |
| MEW | 1 | 165 | 151 |
| PAR | 1 | 182 | Paradox Rift |
| PAF | 1 | 91 | Paldea Fates |
| TEF | 1 | 162 | Temporal Forces |
| TWM | 1 | 167 | Twilight Masquerade |
| SFA | 1 | 64 | Scarlet & Violet—151 |
| SCR | 1 | 142 | Scarlet & Violet—Crown Zenith |
| SSP | 1 | 191 | Scarlet & Violet—Paldea Evolved |
| PRE | 1 | 131 | Scarlet & Violet—Paldea Evolved |
| JTG | 1 | 159 | Scarlet & Violet—Paldea Evolved |
| DRI | 1 | 182 | Scarlet & Violet—Paldea Evolved |
| WHT | 1 | 86 | Scarlet & Violet—Paldea Evolved |
| BLK | 1 | 86 | Scarlet & Violet—Paldea Evolved |

### Configuration File (`config.json`)
```json
{
  "sets": {
    "JTG": {"start": 1, "end": 159, "enabled": true}
  },
  "cache_settings": {
    "max_decklist_threshold": 7
  },
  "scraping_settings": {
    "request_delay": 1.0,
    "max_retries": 3,
    "timeout": 30,
    "user_agent": "Mozilla/5.0..."
  }
}
```

### Cache File (`cache.json`)
```json
{
  "last_search_date": "2024-01-01T10:30:00",
  "cards": {
    "JTG_15": {"decklist_count": 0, "last_checked": "2024-01-01T10:30:00", "skip_permanent": false},
    "JTG_21": {"decklist_count": 12, "last_checked": "2024-01-01T10:30:00", "skip_permanent": true},
    "JTG_45": {"decklist_count": 3, "last_checked": "2024-01-01T10:30:00", "skip_permanent": false}
  }
}
```

## Architecture

### Core Components

#### `limitless_scraper.py`
- **Main scraper class** with intelligent caching
- **Web scraping engine** (requests with retry logic)
- **Rate limiting and error handling**
- **Cache management and persistence**

#### `gui_app.py`
- **Modern tkinter GUI** with two modes
- **Threading for non-blocking operations**
- **Set management dialogs**
- **Real-time progress tracking**

#### `cli_app.py`
- **Comprehensive CLI interface**
- **Multiple output formats**
- **Set management commands**
- **Cache statistics and management**

### Data Flow
1. **Configuration Loading**: Load set configurations from `config.json`
2. **Cache Check**: Check if cards should be skipped based on cache
3. **Web Scraping**: Fetch pages using requests with rate limiting
4. **Data Extraction**: Parse decklist tables and count entries
5. **Cache Update**: Store results with appropriate skip flags
6. **Results Display**: Show results in GUI or CLI format

## Caching Strategy

### Smart Caching Logic
- **>7 decklists**: Permanent skip (won't be re-checked)
- **0 decklists**: Temporary cache (re-check in future runs)
- **1-7 decklists**: Temporary cache (re-check periodically)

### Cache Benefits
- **Efficiency**: Skip cards that won't change
- **Respectful**: Reduce server load
- **Flexibility**: Re-check cards that might change
- **Persistence**: Cache survives application restarts

## Error Handling

### Network Errors
- **Retry logic** with exponential backoff
- **Timeout handling** for slow connections
- **Graceful degradation** when servers are unavailable

### Parsing Errors
- **Robust HTML parsing** with fallback methods
- **Error logging** for debugging
- **Graceful handling** of malformed pages

### Configuration Errors
- **Validation** of set configurations
- **Default values** for missing settings
- **Clear error messages** for invalid configurations

## Performance Considerations

### Optimization Features
- **Intelligent skipping** based on cache
- **Rate limiting** to be respectful to servers
- **Batch processing** for multiple sets
- **Memory-efficient** data structures

### Resource Usage
- **Minimal memory footprint** for large datasets
- **Efficient caching** with JSON persistence
- **Threading** for responsive GUI

## Troubleshooting

### Common Issues

#### Network Connectivity
- Check internet connection
- Verify firewall settings
- Try different network if available

#### Configuration Problems
- Validate JSON syntax in `config.json`
- Check set code formats (must be uppercase)
- Ensure card number ranges are valid

### Logging
- Logs are written to `scraper.log`
- GUI shows real-time log entries
- CLI provides verbose output option

## Development

### Project Structure
```
pkmnOnlineLimitlessRarePlacingCardsJapanTournaments/
├── limitless_scraper.py      # Core scraping logic
├── gui_app.py               # GUI application
├── cli_app.py               # CLI application
├── config.json              # Configuration file
├── requirements.txt         # Python dependencies
├── build_exe.bat            # Build script for .exe
├── README.md               # This file
├── cache.json              # Cache file (created automatically)
└── scraper.log             # Log file (created automatically)
```

### Adding New Features
1. **Extend scraper class** in `limitless_scraper.py`
2. **Update GUI** in `gui_app.py` for new features
3. **Add CLI commands** in `cli_app.py`
4. **Update documentation** in `README.md`

### Building the .exe
To build a standalone Windows executable (no Python required to run):

```bash
# Install PyInstaller if not already installed
pip install pyinstaller

# Run the build script (runs tests first, then builds)
build_exe.bat
```

The resulting `LimitlessTCGScraper.exe` will be in the project root. Upload it to a [GitHub Release](../../releases) for distribution.

### Testing
```bash
# Test scraper functionality
python -c "from limitless_scraper import LimitlessScraper; s = LimitlessScraper(); print('Scraper initialized successfully')"

# Test GUI
python run_gui.py

# Test CLI
python cli_app.py stats
```

## License

This project is provided as-is for educational and research purposes. Please respect the terms of service of LimitlessTCG when using this scraper.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in `scraper.log`
3. Test with a small set first
4. Create an issue with detailed information

## Changelog

### Version 1.0.0
- Initial release
- GUI and CLI interfaces
- Intelligent caching system
- Set management functionality
- Export capabilities
- Comprehensive error handling 