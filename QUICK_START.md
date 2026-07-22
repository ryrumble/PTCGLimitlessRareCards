# Quick Start Guide

## 🚀 Get Started in 3 Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application

#### Option A: GUI Application (Recommended)
```bash
python run_gui.py
```
Or double-click `run_gui.bat` on Windows.

#### Option B: CLI Application
```bash
# View cache statistics
python cli_app.py stats

# List configured sets
python cli_app.py sets list

# View cached results
python cli_app.py view
```

### 3. Start Scraping

#### In GUI:
1. Switch to "Search" mode
2. Select sets to scrape
3. Click "Start Search"

#### In CLI:
```bash
# Scrape specific sets
python cli_app.py scrape JTG SVI

# Scrape with verbose output
python cli_app.py scrape JTG --verbose
```

## 🎯 What You'll Get

- **Smart caching** that skips cards with >7 decklists permanently
- **Target identification** of cards with 1-7 decklists (the "sweet spot")
- **Export options** in CSV, Excel, and JSON formats
- **Set management** to add/edit/remove card sets
- **Real-time progress** tracking during scraping

## 📊 Understanding Results

- **Target Range (1-7 decklists)**: These are the cards you're looking for
- **Permanent Skips (>7 decklists)**: Cards that won't be re-checked
- **Zero Results**: Cards with no decklists (re-checked in future runs)

## 🔧 Configuration

Edit `config.json` to:
- Add new card sets
- Modify card ranges
- Adjust scraping settings

## 🆘 Need Help?

- Run `python test_scraper.py` to verify installation
- Check `scraper.log` for detailed error messages
- Use `python cli_app.py --help` for CLI options

## 📁 Files Created

- `cache.json`: Stores scraping results
- `scraper.log`: Application logs
- `exported_results.csv`: When you export data

## ⚡ Pro Tips

1. **Start small**: Test with 1-2 sets first
2. **Use View Results mode**: Check cached data without scraping
3. **Export regularly**: Save your findings in multiple formats
4. **Monitor logs**: Check `scraper.log` for issues

## 🎮 Example Workflow

1. **Launch GUI**: `python run_gui.py`
2. **Check existing data**: Switch to "View Results" mode
3. **Configure sets**: Click "Manage Sets" to add/edit sets
4. **Start scraping**: Switch to "Search" mode, select sets, click "Start"
5. **Export results**: Use "Export" button to save data
6. **Analyze**: Look for cards in the 1-7 decklist range

Happy scraping! 🎉
