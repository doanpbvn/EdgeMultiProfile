"""Main GUI (customtkinter) for the Edge Multi Profile app."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import __app_name__, __version__, config
from .edge_launcher import close_all_in_dir, close_profile, launch_profiles
from .profile_manager import Profile, ProfileManager

# ----- Design tokens (colors / spacing / radius) -----
COLOR_BG = "#0f172a"
COLOR_SURFACE = "#1e293b"
COLOR_SURFACE_2 = "#273449"
COLOR_PRIMARY = "#2563eb"
COLOR_PRIMARY_HOVER = "#1d4ed8"
COLOR_DANGER = "#dc2626"
COLOR_DANGER_HOVER = "#b91c1c"
COLOR_SUCCESS = "#16a34a"
COLOR_MUTED = "#94a3b8"
COLOR_TEXT = "#e2e8f0"

PAD_XS, PAD_SM, PAD_MD, PAD_LG = 4, 8, 12, 16
RADIUS = 10

# Icon-only buttons use the Segoe MDL2 Assets font shipped with Windows 10/11.
# Glyphs live in the Private Use Area (BMP), so they render reliably on Tk 8.6.
ICON_FONT_FAMILY = "Segoe MDL2 Assets"
ICON_SIZE = 18
ICON_ADD = "\uE710"        # Add
ICON_SELECT_ALL = "\uE8B3"  # SelectAll
ICON_OPEN = "\uE768"       # Play
ICON_OPEN_ALL = "\uE8A7"   # OpenInNewWindow
ICON_FOLDER = "\uE8B7"     # Folder
ICON_SETTINGS = "\uE713"   # Setting (gear)
ICON_RENAME = "\uE70F"     # Edit (pencil)
ICON_DELETE = "\uE74D"     # Delete (trash)

ICON_BTN_SIZE = 40


class Tooltip:
    """Lightweight hover tooltip so icon-only buttons stay understandable."""

    def __init__(self, widget, text: str, delay_ms: int = 400):
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _show(self) -> None:
        if self._tip is not None:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        self._tip = tk.Toplevel(self.widget)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            self._tip, text=self.text, justify="left",
            bg=COLOR_SURFACE_2, fg=COLOR_TEXT, padx=8, pady=4,
            font=("Segoe UI", 9), bd=0,
        )
        label.pack()

    def _hide(self, _event=None) -> None:
        self._cancel()
        if self._tip is not None:
            self._tip.destroy()
            self._tip = None

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None


class ProfileRow(ctk.CTkFrame):
    """A single profile row: checkbox + name + icon actions."""

    def __init__(self, master, profile: Profile, icon_font,
                 on_launch, on_delete, on_rename):
        super().__init__(master, fg_color=COLOR_SURFACE_2, corner_radius=RADIUS)
        self.profile = profile
        self.checked = ctk.BooleanVar(value=False)

        self.grid_columnconfigure(1, weight=1)

        self.checkbox = ctk.CTkCheckBox(
            self, text="", variable=self.checked, width=24,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
        )
        self.checkbox.grid(row=0, column=0, padx=(PAD_MD, PAD_SM), pady=PAD_SM)

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew", pady=PAD_SM)
        info.grid_columnconfigure(0, weight=1)
        self.name_label = ctk.CTkLabel(
            info, text=profile.name, anchor="w",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=COLOR_TEXT,
        )
        self.name_label.grid(row=0, column=0, sticky="w")
        self.sub_label = ctk.CTkLabel(
            info, text=profile.folder, anchor="w",
            font=ctk.CTkFont(size=11), text_color=COLOR_MUTED,
        )
        self.sub_label.grid(row=1, column=0, sticky="w")

        self.launch_btn = ctk.CTkButton(
            self, text=ICON_OPEN, width=ICON_BTN_SIZE, font=icon_font, corner_radius=RADIUS,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            command=lambda: on_launch(profile),
        )
        self.launch_btn.grid(row=0, column=2, padx=PAD_XS, pady=PAD_SM)
        Tooltip(self.launch_btn, "Open this profile")

        self.rename_btn = ctk.CTkButton(
            self, text=ICON_RENAME, width=ICON_BTN_SIZE, font=icon_font, corner_radius=RADIUS,
            fg_color=COLOR_SURFACE, hover_color=COLOR_PRIMARY,
            command=lambda: on_rename(profile),
        )
        self.rename_btn.grid(row=0, column=3, padx=PAD_XS, pady=PAD_SM)
        Tooltip(self.rename_btn, "Rename")

        self.delete_btn = ctk.CTkButton(
            self, text=ICON_DELETE, width=ICON_BTN_SIZE, font=icon_font, corner_radius=RADIUS,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            command=lambda: on_delete(profile),
        )
        self.delete_btn.grid(row=0, column=4, padx=(PAD_XS, PAD_MD), pady=PAD_SM)
        Tooltip(self.delete_btn, "Delete")

    def is_checked(self) -> bool:
        return bool(self.checked.get())

    def set_checked(self, value: bool) -> None:
        self.checked.set(value)


class App(ctk.CTk):
    """Main window."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.manager = ProfileManager()
        self.settings = config.load_settings()
        self.rows: list[ProfileRow] = []
        self._busy = False
        self.icon_font = ctk.CTkFont(family=ICON_FONT_FAMILY, size=ICON_SIZE)

        self.title(f"{__app_name__} v{__version__}")
        self.geometry("860x620")
        self.minsize(760, 540)
        self.configure(fg_color=COLOR_BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_list()
        self._build_statusbar()

        self.refresh_list()

    # ---------- header ----------
    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            header, text="Edge Multi Profile",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=COLOR_TEXT,
        )
        title.grid(row=0, column=0, sticky="w", padx=PAD_LG, pady=(PAD_MD, 0))
        subtitle = ctk.CTkLabel(
            header, text="Manage and open multiple isolated Microsoft Edge profiles",
            font=ctk.CTkFont(size=12), text_color=COLOR_MUTED,
        )
        subtitle.grid(row=1, column=0, sticky="w", padx=PAD_LG, pady=(0, PAD_MD))

        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.grid(row=0, column=1, rowspan=2, padx=PAD_LG, pady=PAD_MD)

        self.open_folder_btn = ctk.CTkButton(
            actions, text=ICON_FOLDER, width=ICON_BTN_SIZE, font=self.icon_font,
            corner_radius=RADIUS, fg_color=COLOR_SURFACE_2, hover_color=COLOR_PRIMARY,
            command=self.open_profiles_folder,
        )
        self.open_folder_btn.grid(row=0, column=0, padx=(0, PAD_SM))
        Tooltip(self.open_folder_btn, "Open profiles folder")

        self.settings_btn = ctk.CTkButton(
            actions, text=ICON_SETTINGS, width=ICON_BTN_SIZE, font=self.icon_font,
            corner_radius=RADIUS, fg_color=COLOR_SURFACE_2, hover_color=COLOR_PRIMARY,
            command=self.open_settings,
        )
        self.settings_btn.grid(row=0, column=1)
        Tooltip(self.settings_btn, "Settings")

    # ---------- toolbar ----------
    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=PAD_LG, pady=(PAD_MD, PAD_SM))
        bar.grid_columnconfigure(0, weight=1)

        self.new_name = ctk.CTkEntry(
            bar, placeholder_text="New profile name...", corner_radius=RADIUS,
            fg_color=COLOR_SURFACE, border_color=COLOR_SURFACE_2,
        )
        self.new_name.grid(row=0, column=0, sticky="ew", padx=(0, PAD_SM), ipady=4)
        self.new_name.bind("<Return>", lambda _e: self.add_profile())

        add_btn = ctk.CTkButton(
            bar, text=ICON_ADD, width=ICON_BTN_SIZE, font=self.icon_font,
            corner_radius=RADIUS, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            command=self.add_profile,
        )
        add_btn.grid(row=0, column=1, padx=PAD_XS)
        Tooltip(add_btn, "Add profile")

        self.select_all_btn = ctk.CTkButton(
            bar, text=ICON_SELECT_ALL, width=ICON_BTN_SIZE, font=self.icon_font,
            corner_radius=RADIUS, fg_color=COLOR_SURFACE_2, hover_color=COLOR_PRIMARY,
            command=self.toggle_select_all,
        )
        self.select_all_btn.grid(row=0, column=2, padx=PAD_XS)
        Tooltip(self.select_all_btn, "Select / deselect all")

        self.launch_sel_btn = ctk.CTkButton(
            bar, text=ICON_OPEN, width=ICON_BTN_SIZE, font=self.icon_font,
            corner_radius=RADIUS, fg_color=COLOR_SUCCESS, hover_color="#15803d",
            command=self.launch_selected,
        )
        self.launch_sel_btn.grid(row=0, column=3, padx=PAD_XS)
        Tooltip(self.launch_sel_btn, "Open selected profiles")

        self.launch_all_btn = ctk.CTkButton(
            bar, text=ICON_OPEN_ALL, width=ICON_BTN_SIZE, font=self.icon_font,
            corner_radius=RADIUS, fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER,
            command=self.launch_all,
        )
        self.launch_all_btn.grid(row=0, column=4, padx=(PAD_XS, 0))
        Tooltip(self.launch_all_btn, "Open all profiles")

    # ---------- profile list ----------
    def _build_list(self) -> None:
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLOR_SURFACE, corner_radius=RADIUS,
            label_text="Profiles", label_text_color=COLOR_MUTED,
        )
        self.list_frame.grid(row=2, column=0, sticky="nsew", padx=PAD_LG, pady=PAD_SM)
        self.list_frame.grid_columnconfigure(0, weight=1)

        self.empty_label = ctk.CTkLabel(
            self.list_frame,
            text="No profiles yet.\nEnter a name above and click \"+ Add profile\".",
            font=ctk.CTkFont(size=13), text_color=COLOR_MUTED,
        )

    # ---------- status bar ----------
    def _build_statusbar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=COLOR_SURFACE, corner_radius=0)
        bar.grid(row=3, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)
        self.status_label = ctk.CTkLabel(
            bar, text="", anchor="w",
            font=ctk.CTkFont(size=11), text_color=COLOR_MUTED,
        )
        self.status_label.grid(row=0, column=0, sticky="ew", padx=PAD_LG, pady=PAD_SM)
        self._update_status()

    def _edge_label(self) -> str:
        path = self.settings.get("edge_path") or "(not found)"
        return path

    def _update_status(self, extra: str = "") -> None:
        count = len(self.manager.profiles)
        base = f"Total: {count} profile(s)  |  Edge: {self._edge_label()}"
        self.status_label.configure(text=f"{extra}   {base}" if extra else base)

    # ---------- list actions ----------
    def refresh_list(self) -> None:
        for row in self.rows:
            row.destroy()
        self.rows.clear()
        self.empty_label.grid_forget()

        profiles = self.manager.profiles
        if not profiles:
            self.empty_label.grid(row=0, column=0, pady=40)
        else:
            for i, profile in enumerate(profiles):
                row = ProfileRow(
                    self.list_frame, profile, self.icon_font,
                    on_launch=self.launch_one,
                    on_delete=self.delete_profile,
                    on_rename=self.rename_profile,
                )
                row.grid(row=i, column=0, sticky="ew", pady=PAD_XS, padx=PAD_XS)
                self.rows.append(row)
        self._update_status()

    def add_profile(self) -> None:
        name = self.new_name.get().strip()
        if not name:
            name = self.manager.default_name()
        try:
            self.manager.add(name)
        except (ValueError, OSError) as exc:
            messagebox.showerror(__app_name__, f"Cannot create profile:\n{exc}")
            return
        self.new_name.delete(0, tk.END)
        self.refresh_list()

    def rename_profile(self, profile: Profile) -> None:
        dialog = ctk.CTkInputDialog(text="New profile name:", title="Rename")
        new_name = dialog.get_input()
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            return
        try:
            self.manager.rename(profile.id, new_name)
        except (ValueError, KeyError) as exc:
            messagebox.showerror(__app_name__, f"Cannot rename:\n{exc}")
            return
        self.refresh_list()

    def delete_profile(self, profile: Profile) -> None:
        confirm = messagebox.askyesno(
            __app_name__,
            f"Delete profile \"{profile.name}\"?\n"
            "Any open Edge window for this profile will be closed first, then all "
            "browsing data (cookies, logins) of this profile will be removed.",
        )
        if not confirm:
            return
        if self._busy:
            return
        self._set_busy(True)
        self._update_status(f"Closing and deleting \"{profile.name}\"...")

        def worker() -> None:
            # Close Edge first so Windows releases file locks on the data folder.
            close_profile(profile)
            self.after(0, lambda: self._finish_delete(profile))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_delete(self, profile: Profile) -> None:
        removed = self.manager.delete(profile.id, remove_data=True)
        self._set_busy(False)
        self.refresh_list()
        if not removed:
            messagebox.showwarning(
                __app_name__,
                f"Profile \"{profile.name}\" was removed from the list, but some "
                "files are still locked. Close Edge completely and use "
                "Settings > Clear profiles folder to clean up.",
            )

    def toggle_select_all(self) -> None:
        any_unchecked = any(not r.is_checked() for r in self.rows)
        for row in self.rows:
            row.set_checked(any_unchecked)

    # ---------- launching ----------
    def _selected_profiles(self) -> list[Profile]:
        return [r.profile for r in self.rows if r.is_checked()]

    def launch_one(self, profile: Profile) -> None:
        self._launch([profile])

    def launch_selected(self) -> None:
        profiles = self._selected_profiles()
        if not profiles:
            messagebox.showinfo(__app_name__, "No profile selected.")
            return
        self._launch(profiles)

    def launch_all(self) -> None:
        profiles = self.manager.profiles
        if not profiles:
            messagebox.showinfo(__app_name__, "No profiles to open.")
            return
        self._launch(profiles)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for btn in (self.launch_sel_btn, self.launch_all_btn):
            btn.configure(state=state)

    def _launch(self, profiles: list[Profile]) -> None:
        if self._busy:
            return
        edge_path = self.settings.get("edge_path", "")
        if not edge_path:
            messagebox.showerror(
                __app_name__,
                "Microsoft Edge path is not set.\n"
                "Go to Settings to select msedge.exe.",
            )
            return

        start_urls = list(self.settings.get("start_urls", []))
        delay = int(self.settings.get("launch_delay_ms", 600))
        self._set_busy(True)
        self._update_status(f"Opening {len(profiles)} profile(s)...")

        def worker() -> None:
            results = launch_profiles(edge_path, profiles, start_urls, delay)
            errors = [(p, e) for p, e in results if e]
            self.after(0, lambda: self._launch_done(len(profiles), errors))

        threading.Thread(target=worker, daemon=True).start()

    def _launch_done(self, total: int, errors: list[tuple[Profile, str]]) -> None:
        self._set_busy(False)
        ok = total - len(errors)
        self._update_status(f"Opened {ok}/{total} profile(s).")
        if errors:
            detail = "\n".join(f"- {p.name}: {e}" for p, e in errors[:8])
            messagebox.showerror(
                __app_name__, f"Some profiles could not be opened:\n{detail}"
            )

    # ---------- folder ----------
    def open_profiles_folder(self) -> None:
        try:
            config.open_in_explorer(config.PROFILES_DIR)
        except OSError as exc:
            messagebox.showerror(__app_name__, f"Cannot open folder:\n{exc}")

    # ---------- settings ----------
    def open_settings(self) -> None:
        SettingsDialog(
            self, self.settings,
            on_save=self._on_settings_saved,
            on_clear=self.clear_profiles,
        )

    def _on_settings_saved(self, new_settings: dict) -> None:
        self.settings = new_settings
        config.save_settings(new_settings)
        self._update_status("Settings saved.")

    def clear_profiles(self) -> None:
        """Close every session under the profiles folder, then wipe it."""
        if self._busy:
            return
        self._set_busy(True)
        self._update_status("Clearing profiles folder...")

        def worker() -> None:
            close_all_in_dir(config.PROFILES_DIR)
            self.after(0, self._finish_clear)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_clear(self) -> None:
        ok = self.manager.clear_all()
        self._set_busy(False)
        self.refresh_list()
        if ok:
            self._update_status("Profiles folder cleared.")
        else:
            messagebox.showwarning(
                __app_name__,
                "Some files are still locked and could not be removed. "
                "Close Edge completely and try again.",
            )


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog: Edge path, start URLs, launch delay, maintenance."""

    def __init__(self, master, settings: dict, on_save, on_clear):
        super().__init__(master)
        self.on_save = on_save
        self.on_clear = on_clear
        self.title("Settings")
        self.geometry("580x520")
        self.configure(fg_color=COLOR_BG)
        self.transient(master)
        self.grab_set()
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Path to msedge.exe", text_color=COLOR_TEXT).grid(
            row=0, column=0, sticky="w", padx=PAD_LG, pady=(PAD_LG, PAD_XS)
        )
        self.edge_entry = ctk.CTkEntry(self, corner_radius=RADIUS, fg_color=COLOR_SURFACE)
        self.edge_entry.insert(0, settings.get("edge_path", ""))
        self.edge_entry.grid(row=1, column=0, columnspan=2, sticky="ew", padx=(PAD_LG, PAD_SM))
        ctk.CTkButton(
            self, text="Browse...", width=80, corner_radius=RADIUS,
            fg_color=COLOR_SURFACE_2, hover_color=COLOR_PRIMARY,
            command=self._browse_edge,
        ).grid(row=1, column=2, padx=(0, PAD_LG))

        ctk.CTkLabel(
            self, text="Start URLs (one per line, leave empty for none)",
            text_color=COLOR_TEXT,
        ).grid(row=2, column=0, columnspan=3, sticky="w", padx=PAD_LG, pady=(PAD_MD, PAD_XS))
        self.url_box = ctk.CTkTextbox(
            self, height=120, corner_radius=RADIUS, fg_color=COLOR_SURFACE,
        )
        self.url_box.insert("1.0", "\n".join(settings.get("start_urls", [])))
        self.url_box.grid(row=3, column=0, columnspan=3, sticky="ew", padx=PAD_LG)

        ctk.CTkLabel(self, text="Delay between launches (ms)", text_color=COLOR_TEXT).grid(
            row=4, column=0, sticky="w", padx=PAD_LG, pady=(PAD_MD, PAD_XS)
        )
        self.delay_entry = ctk.CTkEntry(self, corner_radius=RADIUS, fg_color=COLOR_SURFACE, width=120)
        self.delay_entry.insert(0, str(settings.get("launch_delay_ms", 600)))
        self.delay_entry.grid(row=5, column=0, sticky="w", padx=PAD_LG)

        # Maintenance section
        ctk.CTkLabel(
            self, text="Maintenance", text_color=COLOR_MUTED,
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=6, column=0, columnspan=3, sticky="w", padx=PAD_LG, pady=(PAD_MD, PAD_XS))
        ctk.CTkButton(
            self, text="Clear profiles folder", corner_radius=RADIUS,
            fg_color=COLOR_DANGER, hover_color=COLOR_DANGER_HOVER,
            command=self._clear_profiles,
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=PAD_LG)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=8, column=0, columnspan=3, sticky="e", padx=PAD_LG, pady=PAD_LG)
        ctk.CTkButton(
            btns, text="Cancel", width=90, corner_radius=RADIUS,
            fg_color=COLOR_SURFACE_2, hover_color=COLOR_DANGER, command=self.destroy,
        ).grid(row=0, column=0, padx=PAD_XS)
        ctk.CTkButton(
            btns, text="Save", width=90, corner_radius=RADIUS,
            fg_color=COLOR_PRIMARY, hover_color=COLOR_PRIMARY_HOVER, command=self._save,
        ).grid(row=0, column=1, padx=PAD_XS)

    def _browse_edge(self) -> None:
        path = filedialog.askopenfilename(
            title="Select msedge.exe",
            filetypes=[("Edge", "msedge.exe"), ("All files", "*.*")],
        )
        if path:
            self.edge_entry.delete(0, tk.END)
            self.edge_entry.insert(0, path)

    def _parse_urls(self) -> list[str]:
        raw = self.url_box.get("1.0", tk.END)
        return [line.strip() for line in raw.splitlines() if line.strip()]

    def _clear_profiles(self) -> None:
        confirm = messagebox.askyesno(
            "Clear profiles folder",
            "This will close all open Edge profiles and permanently delete "
            "everything inside EdgeProfiles\\profiles.\n\nContinue?",
            parent=self,
        )
        if not confirm:
            return
        self.on_clear()
        self.destroy()

    def _save(self) -> None:
        try:
            delay = int(self.delay_entry.get().strip() or "0")
            delay = max(0, delay)
        except ValueError:
            messagebox.showwarning("Settings", "Delay must be an integer.", parent=self)
            return
        new_settings = {
            "edge_path": self.edge_entry.get().strip(),
            "start_urls": self._parse_urls(),
            "launch_delay_ms": delay,
        }
        self.on_save(new_settings)
        self.destroy()


def run() -> None:
    config.ensure_dirs()
    app = App()
    app.mainloop()
