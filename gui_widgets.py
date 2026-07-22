"""
Widget classes for the LimitlessTCG Scraper GUI.

Contains SetManagementDialog and SetEditDialog, extracted from gui_app.py.
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


class SetManagementDialog:
    """Dialog for managing set configurations."""

    def __init__(self, parent, config: dict):
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
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)

        title_label = ttk.Label(main_frame, text="Manage Set Configurations", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))

        list_frame = ttk.LabelFrame(main_frame, text="Sets", padding="5")
        list_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        columns = ("Set Code", "Start", "End", "Regulation", "Skip G", "Dup skips")
        self.sets_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=10)

        widths = {"Set Code": 72, "Start": 52, "End": 52, "Regulation": 88, "Skip G": 56, "Dup skips": 72}
        for col in columns:
            self.sets_tree.heading(col, text=col)
            self.sets_tree.column(col, width=widths.get(col, 90))

        self.sets_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.sets_tree.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.sets_tree.configure(yscrollcommand=scrollbar.set)

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))

        ttk.Button(buttons_frame, text="Add Set", command=self._add_set).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Edit Set", command=self._edit_set).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Remove Set", command=self._remove_set).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Import", command=self._import_sets).pack(side=tk.LEFT, padx=5)
        ttk.Button(buttons_frame, text="Export", command=self._export_sets).pack(side=tk.LEFT, padx=5)

        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=3, column=0, columnspan=3)

        ttk.Button(bottom_frame, text="Save & Close", command=self._save_and_close).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)

    def _load_sets(self):
        """Load sets into the treeview."""
        for item in self.sets_tree.get_children():
            self.sets_tree.delete(item)

        for set_code, set_data in self.config["sets"].items():
            reg = (set_data.get("regulation") or "").strip() or "\u2014"
            skip_g = "Yes" if set_data.get("skip_g_regulation_cards", True) else "No"
            dups = set_data.get("duplicate_skip_numbers") or []
            dup_note = str(len(dups)) if dups else "\u2014"
            self.sets_tree.insert(
                "", tk.END, values=(set_code, set_data["start"], set_data["end"], reg, skip_g, dup_note)
            )

    def _add_set(self):
        """Add a new set."""
        dialog = SetEditDialog(self.dialog, None)
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            set_code, set_data = dialog.result
            self.config["sets"][set_code] = set_data
            self._load_sets()

    def _edit_set(self):
        """Edit selected set."""
        selection = self.sets_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a set to edit.")
            return

        item = self.sets_tree.item(selection[0])
        set_code = str(item["values"][0])
        set_data = self.config["sets"][set_code]

        dialog = SetEditDialog(self.dialog, (set_code, set_data))
        self.dialog.wait_window(dialog.dialog)
        if dialog.result:
            new_set_code, new_set_data = dialog.result
            if new_set_code != set_code:
                del self.config["sets"][set_code]
            self.config["sets"][new_set_code] = new_set_data
            self._load_sets()

    def _remove_set(self):
        """Remove selected set."""
        selection = self.sets_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a set to remove.")
            return

        item = self.sets_tree.item(selection[0])
        set_code = str(item["values"][0])

        if messagebox.askyesno("Confirm Removal", f"Are you sure you want to remove set {set_code}?"):
            del self.config["sets"][set_code]
            self._load_sets()

    def _import_sets(self):
        """Import sets from file."""
        filename = filedialog.askopenfilename(
            title="Import Sets", filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename) as f:
                    imported_config = json.load(f)
                self.config["sets"].update(imported_config.get("sets", {}))
                self._load_sets()
                messagebox.showinfo("Success", "Sets imported successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import sets: {e}")

    def _export_sets(self):
        """Export sets to file."""
        filename = filedialog.asksaveasfilename(
            title="Export Sets", defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                export_data = {"sets": self.config["sets"]}
                with open(filename, "w") as f:
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

    def __init__(self, parent, set_data: tuple | None):
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

        self.dialog.columnconfigure(0, weight=1)
        self.dialog.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

        row = 0
        ttk.Label(main_frame, text="Set Code:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.set_code_var = tk.StringVar()
        self.set_code_entry = ttk.Entry(main_frame, textvariable=self.set_code_var)
        self.set_code_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        ttk.Label(main_frame, text="Start Number:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.start_var = tk.StringVar()
        self.start_entry = ttk.Entry(main_frame, textvariable=self.start_var)
        self.start_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        ttk.Label(main_frame, text="End Number:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.end_var = tk.StringVar()
        self.end_entry = ttk.Entry(main_frame, textvariable=self.end_var)
        self.end_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)
        row += 1

        ttk.Label(main_frame, text="Regulation (note):").grid(row=row, column=0, sticky=tk.NW, pady=5)
        self.regulation_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=self.regulation_var).grid(
            row=row, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5
        )
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
            row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(4, 0)
        )
        ttk.Label(main_frame, text="Comma or space separated, e.g. 71, 72, 76", font=("Arial", 9)).grid(
            row=row + 1, column=0, columnspan=2, sticky=tk.W
        )
        row += 2

        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=row, column=0, columnspan=2, pady=14)

        ttk.Button(buttons_frame, text="Save", command=self._save).pack(side=tk.RIGHT, padx=5)
        ttk.Button(buttons_frame, text="Cancel", command=self._cancel).pack(side=tk.RIGHT, padx=5)

    def _load_data(self, set_data):
        """Load existing set data into the form."""
        set_code, data = set_data
        self.set_code_var.set(set_code)
        self.start_var.set(str(data["start"]))
        self.end_var.set(str(data["end"]))
        self.regulation_var.set(data.get("regulation", "") or "")
        self.skip_g_regulation_var.set(data.get("skip_g_regulation_cards", True))
        dups = data.get("duplicate_skip_numbers") or []
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
        duplicate_skip_numbers: list[int] = []
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
            prev_enabled = self.set_data[1].get("enabled", True)

        self.result = (
            set_code,
            {
                "start": start,
                "end": end,
                "enabled": prev_enabled,
                "regulation": self.regulation_var.get().strip(),
                "skip_g_regulation_cards": self.skip_g_regulation_var.get(),
                "duplicate_skip_numbers": duplicate_skip_numbers,
            },
        )
        self.dialog.destroy()

    def _cancel(self):
        """Cancel and close dialog."""
        self.dialog.destroy()
