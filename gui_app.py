"""
LimitlessTCG Scraper GUI Application

This module provides a modern tkinter GUI for the LimitlessTCG scraper with
Search and View Results modes, set management, and comprehensive functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import json
import copy
import webbrowser
from datetime import datetime
from typing import List, Dict, Optional
import pandas as pd
from limitless_scraper import LimitlessScraper, CardResult
from regulation_filter import is_g_regulation


class SetManagementDialog:
    """Dialog for managing set configurations."""
    
    def __init__(self, parent, config: Dict):
        self.parent = parent
        self.config = config
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Set Management")
        self.dialog.geometry("720x520")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_sets()
        
    def _create_widgets(self):
        """Create the dialog widgets."""
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Manage Set Configurations", 
                               font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Sets list
        list_frame = ttk.LabelFrame(main_frame, text="Sets", padding="5")
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Treeview for sets
        columns = ("Set Code", "Start", "End", "Regulation", "Skip G", "Dup skips")
        self.sets_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)
        
        widths = {"Set Code": 72, "Start": 52, "End": 52, "Regulation": 88, "Skip G": 56, "Dup skips": 72}
        for col in columns:
            self.sets_tree.heading(col, text=col)
            self.sets_tree.column(col, width=widths.get(col, 90))
            
        self.sets_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sets_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sets_tree.configure(yscrollcommand=scrollbar.set)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        ttk.Button(buttons_frame, text="Add Set", command=self._add_set).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Edit Set", command=self._edit_set).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Remove Set", command=self._remove_set).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Import", command=self._import_sets).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Export", command=self._export_sets).pack(side=tk.LEFT, padx=5)
        
        # Bottom buttons
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=3, column=0, columnspan=3)
        
        ttk.Button(bottom_frame, text="Save & Close", command=self._save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)
        
    def _load_sets(self):
        """Load sets into the treeview."""
        for item in self.sets_tree.get_children():
            self.sets_tree.delete(item)
            
        for set_code, set_data in self.config['sets'].items():
            reg = (set_data.get('regulation') or "").strip() or "—"
            skip_g = "Yes" if set_data.get('skip_g_regulation_cards', True) else "No"
            dups = set_data.get('duplicate_skip_numbers') or []
            dup_note = str(len(dups)) if dups else "—"
            self.sets_tree.insert("", tk.END, values=(
                set_code, set_data['start'], set_data['end'], reg, skip_g, dup_note
            ))
            
    def _add_set(self):
        """Add a new set."""
        dialog = SetEditDialog(self.dialog, None)
        self.dialog.wait_window(dialog.dialog)  # Wait for dialog to close
        if dialog.result:
            set_code, set_data = dialog.result
            self.config['sets'][set_code] = set_data
            self._load_sets()
            
    def _edit_set(self):
        """Edit selected set."""
        selection = self.sets_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a set to edit.")
            return
            
        item = self.sets_tree.item(selection[0])
        set_code = str(item['values'][0])
        set_data = self.config['sets'][set_code]
        
        dialog = SetEditDialog(self.dialog, (set_code, set_data))
        self.dialog.wait_window(dialog.dialog)  # Wait for dialog to close
        if dialog.result:
            new_set_code, new_set_data = dialog.result
            if new_set_code != set_code:
                del self.config['sets'][set_code]
            self.config['sets'][new_set_code] = new_set_data
            self._load_sets()
            
    def _remove_set(self):
        """Remove selected set."""
        selection = self.sets_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a set to remove.")
            return
            
        item = self.sets_tree.item(selection[0])
        set_code = str(item['values'][0])
        
        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove set {set_code}?"):
            del self.config['sets'][set_code]
            self._load_sets()
            
    def _import_sets(self):
        """Import sets from file."""
        filename = filedialog.askopenfilename(
            title="Import Sets",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    imported_config = json.load(f)
                self.config['sets'].update(imported_config.get('sets', {}))
                self._load_sets()
                messagebox.showinfo("Success", "Sets imported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import sets: {e}")
                
    def _export_sets(self):
        """Export sets to file."""
        filename = filedialog.asksaveasfilename(
            title="Export Sets",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                export_data = {"sets": self.config['sets']}
                with open(filename, 'w') as f:
                    json.dump(export_data, f, indent=2)
                messagebox.showinfo("Success", "Sets exported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export sets: {e}")
                
    def _save_and_close(self):
        """Save changes and close dialog."""
        self.result = self.config
        self.dialog.destroy()
        
    def _cancel(self):
        """Cancel and close dialog."""
        self.dialog.destroy()


class SetEditDialog:
    """Dialog for editing individual set configurations."""
    
    def __init__(self, parent, set_data: Optional[tuple]):
        self.parent = parent
        self.set_data = set_data
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Edit Set" if set_data else "Add Set")
        self.dialog.geometry("440x340")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        if set_data:
            self._load_data(set_data)
            
    def _create_widgets(self):
        """Create the dialog widgets."""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        row = 0
        # Set Code
        ttk.Label(main_frame, text="Set Code:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.set_code_var = tk.StringVar()
        self.set_code_entry = ttk.Entry(main_frame, textvariable=self.set_code_var)
        self.set_code_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        # Start Number
        ttk.Label(main_frame, text="Start Number:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.start_var = tk.StringVar()
        self.start_entry = ttk.Entry(main_frame, textvariable=self.start_var)
        self.start_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        # End Number
        ttk.Label(main_frame, text="End Number:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.end_var = tk.StringVar()
        self.end_entry = ttk.Entry(main_frame, textvariable=self.end_var)
        self.end_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        # Regulation (note for the set, e.g. G / H / I)
        ttk.Label(main_frame, text="Regulation (note):").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.regulation_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.regulation_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        self.skip_g_regulation_var = tk.BooleanVar(value=True)
        self.skip_g_check = ttk.Checkbutton(
            main_frame,
            text="When searching, skip cards treated as G regulation (uses Limitless rules)",
            variable=self.skip_g_regulation_var,
        )
        self.skip_g_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(4, 0))
        row += 1

        ttk.Label(
            main_frame,
            text="Skip card numbers (duplicates / reprints):",
            wraplength=400,
        ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        row += 1
        self.duplicate_skip_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.duplicate_skip_var).grid(
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(4, 0))
        ttk.Label(main_frame, text="Comma or space separated, e.g. 71, 72, 76", font=("Arial", 9)).grid(
            row=row + 1, column=0, columnspan=2, sticky=tk.W)
        row += 2
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=row, column=0, columnspan=2, pady=14)
        
        ttk.Button(buttons_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)
        
    def _load_data(self, set_data):
        """Load existing set data into the form."""
        set_code, data = set_data
        self.set_code_var.set(set_code)
        self.start_var.set(str(data['start']))
        self.end_var.set(str(data['end']))
        self.regulation_var.set(data.get('regulation', '') or '')
        self.skip_g_regulation_var.set(data.get('skip_g_regulation_cards', True))
        dups = data.get('duplicate_skip_numbers') or []
        self.duplicate_skip_var.set(", ".join(str(n) for n in sorted(dups)))
        
    def _save(self):
        """Save the set data."""
        set_code = self.set_code_var.get().strip().upper()
        if not set_code:
            messagebox.showerror("Error", "Set code is required.")
            return
            
        try:
            start = int(self.start_var.get())
            end = int(self.end_var.get())
            if start > end:
                messagebox.showerror("Error", "Start number must be less than or equal to end number.")
                return
        except ValueError:
            messagebox.showerror("Error", "Start and end numbers must be integers.")
            return

        dup_raw = self.duplicate_skip_var.get().strip()
        duplicate_skip_numbers: List[int] = []
        if dup_raw:
            for part in dup_raw.replace(",", " ").split():
                part = part.strip()
                if not part:
                    continue
                try:
                    duplicate_skip_numbers.append(int(part))
                except ValueError:
                    messagebox.showerror("Error", f"Invalid card number: {part!r}")
                    return
            duplicate_skip_numbers = sorted(set(duplicate_skip_numbers))

        prev_enabled = True
        if self.set_data:
            prev_enabled = self.set_data[1].get('enabled', True)

        self.result = (set_code, {
            'start': start,
            'end': end,
            'enabled': prev_enabled,
            'regulation': self.regulation_var.get().strip(),
            'skip_g_regulation_cards': self.skip_g_regulation_var.get(),
            'duplicate_skip_numbers': duplicate_skip_numbers,
        })
        self.dialog.destroy()
        
    def _cancel(self):
        """Cancel and close dialog."""
        self.dialog.destroy()


class LimitlessScraperGUI:
    """Main GUI application for the LimitlessTCG scraper."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LimitlessTCG Scraper")
        self.root.geometry("1200x800")
        
        # Initialize scraper
        self.scraper = LimitlessScraper()
        self.scraping_thread = None
        self.stop_scraping = False
        self.scraping_results = None
        
        # Create GUI
        self._create_widgets()
        #self._load_cached_results()
        
    def _create_widgets(self):
        """Create the main GUI widgets."""
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(self.root, text="LimitlessTCG Card Scraper", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=10)
        
        # Mode selection
        mode_frame = ttk.LabelFrame(self.root, text="Mode", padding="10")
        mode_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 10))
        mode_frame.columnconfigure(1, weight=1)
        
        self.mode_var = tk.StringVar(value="view")
        
        ttk.Radiobutton(mode_frame, text="View Results", variable=self.mode_var, 
                       value="view", command=self._switch_mode).grid(row=0, column=0, sticky=tk.W)
        ttk.Radiobutton(mode_frame, text="Search", variable=self.mode_var, 
                       value="search", command=self._switch_mode).grid(row=0, column=1, sticky=tk.W, padx=(20, 0))
        
        # Main content area
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=10, pady=(0, 10))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(1, weight=1)
        
        # Create both mode frames
        self._create_view_mode()
        self._create_search_mode()
        
        # Show initial mode
        self._switch_mode()
        
    def _create_view_mode(self):
        """Create the View Results mode widgets."""
        self.view_frame = ttk.Frame(self.content_frame)
        
        # Controls frame
        controls_frame = ttk.Frame(self.view_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        controls_frame.columnconfigure(1, weight=1)
        
        ttk.Label(controls_frame, text="Filter:").grid(row=0, column=0, sticky=tk.W)
        
        self.filter_var = tk.BooleanVar(value=True)
        self.filter_check = ttk.Checkbutton(controls_frame, text="Hide cards with 0 decklists",
                                           variable=self.filter_var, command=self._load_cached_results)
        self.filter_check.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        self.filter_eight_plus_var = tk.BooleanVar(value=False)
        self.filter_eight_plus_check = ttk.Checkbutton(controls_frame, text="Hide cards with >= count",
                                                    variable=self.filter_eight_plus_var, command=self._load_cached_results)
        self.filter_eight_plus_check.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Initialize from config default
        filter_g_default = self.scraper.config.get('filter_settings', {}).get('exclude_g_regulation', True)
        self.filter_g_regulation_var = tk.BooleanVar(value=filter_g_default)
        self.filter_g_regulation_check = ttk.Checkbutton(controls_frame, text="Hide G regulation cards",
                                                         variable=self.filter_g_regulation_var, command=self._load_cached_results)
        self.filter_g_regulation_check.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # Threshold spinbox for decklist count
        self.deck_threshold_var = tk.IntVar(value=8)
        self.deck_threshold_spin = ttk.Spinbox(controls_frame, from_=1, to=999, textvariable=self.deck_threshold_var, width=6, command=self._load_cached_results)
        self.deck_threshold_spin.grid(row=1, column=2, sticky=tk.W, padx=(10, 0))

        ttk.Button(controls_frame, text="Refresh", command=self._load_cached_results).grid(row=0, column=2, padx=(20, 0))
        ttk.Button(controls_frame, text="Export", command=self._export_results).grid(row=0, column=3, padx=(10, 0))
        ttk.Button(controls_frame, text="Clear Cache", command=self._clear_cache).grid(row=0, column=4, padx=(10, 0))
        ttk.Button(controls_frame, text="Manage Sets", command=self._manage_sets).grid(row=0, column=5, padx=(10, 0))

        # Latest tournament month/year filter UI
        ttk.Label(controls_frame, text="Month Filter (MM):").grid(row=1, column=3, sticky=tk.E)
        self.month_filter_var = tk.StringVar(value="")
        ttk.Entry(controls_frame, textvariable=self.month_filter_var, width=6).grid(row=1, column=4, sticky=tk.W)
        
        ttk.Label(controls_frame, text="Year Filter (YYYY):").grid(row=1, column=5, sticky=tk.E, padx=(10, 0))
        self.year_filter_var = tk.StringVar(value="")
        ttk.Entry(controls_frame, textvariable=self.year_filter_var, width=6).grid(row=1, column=6, sticky=tk.W)
        
        # Filter mode selection
        self.filter_mode_var = tk.StringVar(value="exact")
        ttk.Radiobutton(controls_frame, text="Exact", variable=self.filter_mode_var, 
                       value="exact", command=self._load_cached_results).grid(row=1, column=7, sticky=tk.W, padx=(10, 0))
        ttk.Radiobutton(controls_frame, text="≥", variable=self.filter_mode_var, 
                       value="greater_equal", command=self._load_cached_results).grid(row=1, column=8, sticky=tk.W)

        # Card name label (removed per user request)
        self.card_name_label = None

        # Results treeview
        tree_frame = ttk.Frame(self.view_frame)
        tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        columns = ("Set Code", "Card Number", "Card Name", "Decklist Count", "Latest Tournament", "Last Checked")
        self.results_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.results_tree.heading(col, text=col, command=lambda c=col: self._sort_treeview(c))
            self.results_tree.column(col, width=150)
            
        self.results_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_tree.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.results_tree.configure(xscrollcommand=h_scrollbar.set)
        
        # Bind double-click to open card page
        self.results_tree.bind("<Double-1>", self._open_card_page)
        
        # Status bar
        self.view_status_var = tk.StringVar()
        self.view_status_label = ttk.Label(self.view_frame, textvariable=self.view_status_var)
        self.view_status_label.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.S), pady=(10, 0))
        
    def _create_search_mode(self):
        """Create the Search mode widgets."""
        self.search_frame = ttk.Frame(self.content_frame)
        
        # Set selection frame
        set_frame = ttk.LabelFrame(self.search_frame, text="Set Selection", padding="10")
        set_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        set_frame.columnconfigure(1, weight=1)
        
        ttk.Label(set_frame, text="Sets to search:").grid(row=0, column=0, sticky=tk.W)
        
        # Set listbox
        listbox_frame = ttk.Frame(set_frame)
        listbox_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        listbox_frame.columnconfigure(0, weight=1)
        listbox_frame.rowconfigure(0, weight=1)
        
        self.sets_listbox = tk.Listbox(listbox_frame, selectmode=tk.MULTIPLE, height=8)
        self.sets_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for listbox
        listbox_scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.sets_listbox.yview)
        listbox_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sets_listbox.configure(yscrollcommand=listbox_scrollbar.set)
        
        # Buttons frame
        buttons_frame = ttk.Frame(set_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(buttons_frame, text="Select All", command=self._select_all_sets).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Clear Selection", command=self._clear_set_selection).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Manage Sets", command=self._manage_sets).pack(side=tk.LEFT, padx=5)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(self.search_frame, text="Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        ttk.Label(progress_frame, text="Current:").grid(row=0, column=0, sticky=tk.W)
        self.current_var = tk.StringVar(value="Ready")
        self.current_label = ttk.Label(progress_frame, textvariable=self.current_var)
        self.current_label.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        ttk.Label(progress_frame, text="Progress:").grid(row=1, column=0, sticky=tk.W)
        self.progress_var = tk.StringVar(value="0/0")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='determinate')
        self.progress_bar.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Control buttons
        control_frame = ttk.Frame(self.search_frame)
        control_frame.grid(row=2, column=0, pady=(0, 10))
        
        self.start_button = ttk.Button(control_frame, text="Start Search", command=self._start_search)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Search", command=self._stop_search, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # Log frame
        log_frame = ttk.LabelFrame(self.search_frame, text="Log", padding="10")
        log_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status bar
        self.search_status_var = tk.StringVar()
        self.search_status_label = ttk.Label(self.search_frame, textvariable=self.search_status_var)
        self.search_status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def _switch_mode(self):
        """Switch between View Results and Search modes."""
        if self.mode_var.get() == "view":
            self.search_frame.grid_remove()
            self.view_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._load_cached_results()
        else:
            self.view_frame.grid_remove()
            self.search_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            self._load_set_list()
            
    def _load_set_list(self):
        """Load available sets into the listbox."""
        self.sets_listbox.delete(0, tk.END)
        for set_code, set_data in self.scraper.config['sets'].items():
            if set_data.get('enabled', True):
                self.sets_listbox.insert(tk.END, set_code)
                
    def _select_all_sets(self):
        """Select all sets in the listbox."""
        self.sets_listbox.selection_set(0, tk.END)
        
    def _clear_cache(self):
        """Clear the cache."""
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the cache? This will remove all cached results."):
            self.scraper.clear_cache()
            self._load_cached_results()
            messagebox.showinfo("Success", "Cache cleared successfully.")

    def _manage_sets(self):
        """Open set management dialog."""
        config_working = copy.deepcopy(self.scraper.config)
        dialog = SetManagementDialog(self.root, config_working)
        self.root.wait_window(dialog.dialog)
        if dialog.result is None:
            return

        self.scraper.config = dialog.result

        try:
            with open(self.scraper.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.scraper.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Save Failed", f"Could not save config: {e}")
            return

        try:
            self._load_set_list()
        except Exception:
            pass

        messagebox.showinfo("Sets saved", f"Configuration was saved to:\n{self.scraper.config_file}")

    def _clear_set_selection(self):
        """Clear set selection in the listbox."""
        self.sets_listbox.selection_clear(0, tk.END)
        
    def _open_card_page(self, event):
        """Open the LimitlessTCG page for the selected card."""
        selection = self.results_tree.selection()
        if selection:
            item = self.results_tree.item(selection[0])
            set_code = item['values'][0]
            card_number = item['values'][1]
            
            # Construct the URL
            url = f"https://limitlesstcg.com/cards/{set_code}/{card_number}"
            webbrowser.open(url)
    
    def _matches_date_filter(self, latest_tournament, month_filter, year_filter, filter_mode):
        """Check if a tournament date matches the filter criteria."""
        if not latest_tournament:
            return not (month_filter or year_filter)  # Show empty dates only if no filters
        
        try:
            parts = latest_tournament.split('/')
            if len(parts) < 2:
                return not (month_filter or year_filter)
            
            tournament_month = int(parts[0])
            tournament_day = int(parts[1])
            tournament_year = int(parts[2]) if len(parts) > 2 else datetime.now().year
            
            # Handle 2-digit years
            if tournament_year < 100:
                tournament_year += 2000 if tournament_year < 50 else 1900
            
            # Check month filter
            if month_filter:
                filter_month = int(month_filter)
                if filter_mode == "exact":
                    if tournament_month != filter_month:
                        return False
                else:  # greater_equal
                    if tournament_month < filter_month:
                        return False
            
            # Check year filter
            if year_filter:
                filter_year = int(year_filter)
                if filter_mode == "exact":
                    if tournament_year != filter_year:
                        return False
                else:  # greater_equal
                    if tournament_year < filter_year:
                        return False
            
            return True
            
        except (ValueError, IndexError):
            return not (month_filter or year_filter)  # Show invalid dates only if no filters

    def _sort_treeview(self, column):
        """Sort the treeview by the specified column."""
        # Get all items
        items = [(self.results_tree.set(child, column), child) for child in self.results_tree.get_children('')]
        
        # Check if we need to toggle sort direction
        if hasattr(self, '_last_sort_column') and self._last_sort_column == column:
            if not hasattr(self, '_sort_reverse'):
                self._sort_reverse = False
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_reverse = False
        self._last_sort_column = column
        
        # Special handling for Latest Tournament column (chronological sorting)
        if column == "Latest Tournament":
            def parse_date(date_str):
                if not date_str:
                    return (0, 0, 0)  # Empty dates go first
                try:
                    # Handle formats like "09/08", "09/08/2024", "09/08/24"
                    parts = date_str.split('/')
                    if len(parts) == 2:
                        month, day = int(parts[0]), int(parts[1])
                        # Assume current year if no year provided
                        year = datetime.now().year
                        return (year, month, day)
                    elif len(parts) == 3:
                        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
                        # Handle 2-digit years
                        if year < 100:
                            year += 2000 if year < 50 else 1900
                        return (year, month, day)
                except (ValueError, IndexError):
                    pass
                return (0, 0, 0)  # Invalid dates go first
            
            items.sort(key=lambda x: parse_date(x[0]), reverse=self._sort_reverse)
        else:
            # Regular string sorting for other columns
            items.sort(key=lambda x: x[0].lower() if x[0] else "", reverse=self._sort_reverse)
        
        # Rearrange items
        for index, (val, child) in enumerate(items):
            self.results_tree.move(child, '', index)
            
    def _load_cached_results(self):
        """Load cached results into the treeview."""
        if self.scraping_results:
            self._display_results(self.scraping_results)
        else:
            # Clear existing items
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)

            # Get cached results
            filter_zero = self.filter_var.get()
            filter_eight_plus = self.filter_eight_plus_var.get()
            filter_g_regulation = getattr(self, 'filter_g_regulation_var', None).get() if hasattr(self, 'filter_g_regulation_var') else True
            results = self.scraper.get_cached_results(filter_zero_results=filter_zero, filter_g_regulation=filter_g_regulation)

            # Filter results
            filtered_results = []
            # Determine threshold if enabled
            threshold = self.deck_threshold_var.get() if filter_eight_plus else None
            # Month/year filter inputs
            month_filter = getattr(self, 'month_filter_var', None).get().strip() if hasattr(self, 'month_filter_var') else ""
            year_filter = getattr(self, 'year_filter_var', None).get().strip() if hasattr(self, 'year_filter_var') else ""
            filter_mode = getattr(self, 'filter_mode_var', None).get() if hasattr(self, 'filter_mode_var') else "exact"

            for result in results:
                if filter_g_regulation:
                    set_cfg = self.scraper.config.get('sets', {}).get(result.set_code, {})
                    if set_cfg.get('skip_g_regulation_cards', True) and is_g_regulation(
                        result.set_code, result.card_number
                    ):
                        continue
                
                if threshold is not None and result.decklist_count >= threshold:
                    continue
                
                # Apply month/year filter
                latest_tournament = getattr(result, 'latest_tournament', '') or ""
                if month_filter or year_filter:
                    if not self._matches_date_filter(latest_tournament, month_filter, year_filter, filter_mode):
                        continue
                
                filtered_results.append(result)

            # Sort results by set code and card number
            filtered_results.sort(key=lambda x: (x.set_code, x.card_number))

            # Add to treeview
            for result in filtered_results:
                last_checked = result.last_checked.strftime("%Y-%m-%d %H:%M")

                self.results_tree.insert("", tk.END, values=(
                    result.set_code,
                    result.card_number,
                    result.card_name,
                    result.decklist_count,
                    getattr(result, 'latest_tournament', '') or "",
                    last_checked
                ))

            # Update status
            cache_stats = self.scraper.get_cache_stats()
            if cache_stats['last_search_date']:
                last_search = datetime.fromisoformat(cache_stats['last_search_date']).strftime("%Y-%m-%d %H:%M")
                self.view_status_var.set(
                    f"Total cards: {cache_stats['total_cards']} | "
                    f"Target range (1-7): {cache_stats['target_range']} | "
                    f"Last search: {last_search}"
                )
            else:
                self.view_status_var.set(
                    f"Total cards: {cache_stats['total_cards']} | "
                    f"Target range (1-7): {cache_stats['target_range']} | "
                    f"No searches performed yet"
                )
    
    def _export_results(self):
        """Export results to file."""
        filename = filedialog.asksaveasfilename(
            title="Export Results",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if filename:
            try:
                # Get all results (not filtered)
                results = self.scraper.get_cached_results(filter_zero_results=False)

                # Convert to DataFrame
                data = []
                for result in results:
                    data.append({
                        'Set Code': result.set_code,
                        'Card Number': result.card_number,
                        'Card Name': result.card_name,
                        'Decklist Count': result.decklist_count,
                        'Latest Tournament': getattr(result, 'latest_tournament', ''),
                        'Last Checked': result.last_checked,
                        'Skip Permanent': result.skip_permanent
                    })

                df = pd.DataFrame(data)

                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False)
                else:
                    df.to_csv(filename, index=False)

                messagebox.showinfo("Success", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export results: {e}")
    
    def _start_search(self):
        """Start the search process."""
        # Get selected sets
        selected_indices = self.sets_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select at least one set to search.")
            return
        
        selected_sets = [self.sets_listbox.get(i) for i in selected_indices]
        
        # Reset stop flag
        self.stop_scraping = False
        
        # Update UI
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.current_var.set("Starting...")
        self.progress_var.set("0/0")
        self.progress_bar['value'] = 0
        self.log_text.delete(1.0, tk.END)
        
        # Start scraping thread
        self.scraping_thread = threading.Thread(
            target=self._scrape_thread,
            args=(selected_sets,),
            daemon=True
        )
        self.scraping_thread.start()
    
    def _stop_search(self):
        """Stop the search process."""
        self.stop_scraping = True
        self._log("Search stopped by user.")
        
        # Update UI
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.current_var.set("Stopped")
    
    def _scrape_thread(self, selected_sets):
        """Thread function for scraping."""
        try:
            total_cards = 0
            current_card = 0
            
            # Calculate total cards
            for set_code in selected_sets:
                set_data = self.scraper.config['sets'][set_code]
                total_cards += set_data['end'] - set_data['start'] + 1
            
            # Update progress
            self.root.after(0, lambda: self.progress_bar.config(maximum=total_cards))
            
            results = []
            
            for set_code in selected_sets:
                if self.stop_scraping:
                    break
                    
                self.root.after(0, lambda sc=set_code: self._log(f"Starting set {sc}"))
                
                set_data = self.scraper.config['sets'][set_code]
                
                for card_num in range(set_data['start'], set_data['end'] + 1):
                    if self.stop_scraping:
                        break
                    
                    current_card += 1
                    
                    # Update UI
                    self.root.after(0, lambda: self.current_var.set(f"{set_code}-{card_num:03d}"))
                    self.root.after(0, lambda: self.progress_var.set(f"{current_card}/{total_cards}"))
                    self.root.after(0, lambda: self.progress_bar.config(value=current_card))
                    
                    try:
                        # Check if duplicate (skip from search)
                        if self.scraper._should_skip_duplicate(set_code, card_num):
                            self.root.after(0, lambda: self._log(f"Skipping {set_code}-{card_num:03d} (duplicate)"))
                            continue

                        # Check if G regulation (will be skipped by scraper, but check here for logging)
                        if self.scraper._should_skip_g_regulation(set_code, card_num):
                            self.root.after(0, lambda: self._log(f"Skipping {set_code}-{card_num:03d} (G regulation)"))
                            continue
                        
                        # Check cache first
                        if self.scraper._should_skip_card(set_code, card_num):
                            self.root.after(0, lambda: self._log(f"Skipping {set_code}-{card_num:03d} (cached)"))
                            continue
                        
                        # Scrape the card
                        result = self.scraper.scrape_card(set_code, card_num)
                        if result:
                            results.append(result)
                            self.root.after(0, lambda r=result: self._log(
                                f"Found {r.set_code}-{r.card_number:03d}: {r.decklist_count} decklists"
                            ))
                    except Exception as e:
                        self.root.after(0, lambda e=e: self._log(f"Error scraping {set_code}-{card_num:03d}: {e}"))
            
            # Update search complete status
            if not self.stop_scraping:
                self.root.after(0, lambda: self._log("Search completed!"))
                self.root.after(0, lambda: self.current_var.set("Complete"))
                
                # Store results and switch to view mode
                self.scraping_results = results
                self.root.after(0, self._search_complete)
            
        except Exception as e:
            self.root.after(0, lambda: self._log(f"Search error: {e}"))
        finally:
            # Re-enable start button
            self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
    
    def _search_complete(self):
        """Handle search completion."""
        # Switch to view mode
        self.mode_var.set("view")
        self._switch_mode()
        
        # Show results
        messagebox.showinfo("Search Complete", "Search completed! Switching to View Results mode.")
    
    def _display_results(self, results):
        """Display search results in the treeview."""
        # Clear existing items
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Filter results if needed
        filter_zero = self.filter_var.get()
        filter_eight_plus = self.filter_eight_plus_var.get()
        filter_g_regulation = getattr(self, 'filter_g_regulation_var', None).get() if hasattr(self, 'filter_g_regulation_var') else True
        threshold = self.deck_threshold_var.get() if filter_eight_plus else None
        month_filter = getattr(self, 'month_filter_var', None).get().strip() if hasattr(self, 'month_filter_var') else ""
        year_filter = getattr(self, 'year_filter_var', None).get().strip() if hasattr(self, 'year_filter_var') else ""
        filter_mode = getattr(self, 'filter_mode_var', None).get() if hasattr(self, 'filter_mode_var') else "exact"
        
        filtered_results = []
        for result in results:
            if self.scraper.should_skip_duplicate_card(result.set_code, result.card_number):
                continue
            if filter_g_regulation:
                set_cfg = self.scraper.config.get('sets', {}).get(result.set_code, {})
                if set_cfg.get('skip_g_regulation_cards', True) and is_g_regulation(
                    result.set_code, result.card_number
                ):
                    continue
            
            if filter_zero and result.decklist_count == 0:
                continue
            if threshold is not None and result.decklist_count >= threshold:
                continue
            
            # Apply month/year filter
            latest_tournament = getattr(result, 'latest_tournament', '') or ""
            if month_filter or year_filter:
                if not self._matches_date_filter(latest_tournament, month_filter, year_filter, filter_mode):
                    continue
            
            filtered_results.append(result)
        
        # Sort results
        filtered_results.sort(key=lambda x: (x.set_code, x.card_number))
        
        # Add to treeview (align with columns including Latest Tournament)
        for result in filtered_results:
            last_checked = result.last_checked.strftime("%Y-%m-%d %H:%M")
            latest_tournament = getattr(result, 'latest_tournament', '') or ""

            self.results_tree.insert("", tk.END, values=(
                result.set_code,
                result.card_number,
                result.card_name,
                result.decklist_count,
                latest_tournament,
                last_checked
            ))
        
        # Update status
        self.view_status_var.set(f"Found {len(filtered_results)} cards matching criteria")
    
    def _log(self, message):
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def run(self):
        """Run the GUI application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = LimitlessScraperGUI()
    app.run()