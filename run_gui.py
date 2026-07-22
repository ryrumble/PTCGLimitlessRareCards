#!/usr/bin/env python3
"""
Simple launcher for the LimitlessTCG Scraper GUI

This script provides a simple way to launch the GUI application
with proper error handling and setup.
"""

import os
import sys
import traceback


def main():
    """Launch the GUI application."""
    try:
        # Add current directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)

        # Import and run GUI
        from gui_app import LimitlessScraperGUI

        print("Starting LimitlessTCG Scraper GUI...")
        app = LimitlessScraperGUI()
        app.run()

    except ImportError as e:
        print(f"Error: Could not import required modules: {e}")
        print("Please make sure you have installed all dependencies:")
        print("  pip install -r requirements.txt")
        sys.exit(1)

    except Exception as e:
        print(f"Error starting GUI: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
