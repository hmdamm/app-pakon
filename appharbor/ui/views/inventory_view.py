"""Inventory sidebar view conforming to GNOME HIG (Warehouse/Flatseal style)."""

from __future__ import annotations

from typing import Callable, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from appharbor.domain.models import (
    FilterCategory,
    InstallationRecord,
    ScopeEnum,
    SourceEnum,
)
from appharbor.inventory.orchestrator import InventoryOrchestrator, InventorySnapshot
from appharbor.system.capabilities import format_bytes


class InventoryView(Gtk.Box):
    """Sidebar view featuring search, filtering, and a navigation-styled application list."""

    FILTER_ORDER = [
        FilterCategory.ALL,
        FilterCategory.FLATPAK,
        FilterCategory.SNAP,
        FilterCategory.APPIMAGE,
        FilterCategory.SYSTEM,
        FilterCategory.USER,
        FilterCategory.UNKNOWN,
    ]

    def __init__(
        self,
        orchestrator: InventoryOrchestrator,
        on_select_record: Callable[[InstallationRecord], None],
        on_rescan_requested: Optional[Callable[[], None]] = None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.add_css_class("sidebar-pane")

        self._orchestrator = orchestrator
        self._on_select_record = on_select_record
        self._on_rescan_requested = on_rescan_requested

        self._active_category = FilterCategory.ALL
        self._search_text = ""
        self._sort_by = "name"
        self._sort_asc = True

        self._filter_strings = [
            "All Sources",
            "Flatpak",
            "Snap",
            "AppImage",
            "System Scope",
            "User Scope",
            "Unknown",
        ]
        self._string_list = Gtk.StringList.new(self._filter_strings)

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Search Bar & Entry
        self.search_bar = Gtk.SearchBar()
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search installed applications…")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)

        self.search_bar.set_child(self.search_entry)
        self.search_bar.connect_entry(self.search_entry)
        self.append(self.search_bar)

        # 2. Controls Toolbar Bar (Filter Dropdown & Sort)
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.set_margin_start(12)
        controls_box.set_margin_end(12)
        controls_box.set_margin_top(8)
        controls_box.set_margin_bottom(6)

        # Filter Dropdown
        self.filter_dropdown = Gtk.DropDown(model=self._string_list)
        self.filter_dropdown.set_hexpand(True)
        self.filter_dropdown.set_tooltip_text("Filter applications by packaging source or scope")
        self.filter_dropdown.connect("notify::selected", self._on_filter_changed)
        controls_box.append(self.filter_dropdown)

        # Sort Dropdown
        sort_strings = Gtk.StringList.new(["Name (A-Z)", "Source", "Scope", "Size"])
        self.sort_dropdown = Gtk.DropDown(model=sort_strings)
        self.sort_dropdown.set_tooltip_text("Sort list")
        self.sort_dropdown.connect("notify::selected", self._on_sort_changed)
        controls_box.append(self.sort_dropdown)

        self.append(controls_box)

        # 3. Compact Sub-header summary label
        summary_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        summary_box.set_margin_start(16)
        summary_box.set_margin_end(16)
        summary_box.set_margin_bottom(6)

        self.summary_lbl = Gtk.Label(label="Scanning applications…")
        self.summary_lbl.add_css_class("caption")
        self.summary_lbl.add_css_class("dim-label")
        self.summary_lbl.set_halign(Gtk.Align.START)
        summary_box.append(self.summary_lbl)
        self.append(summary_box)

        # 4. View Stack (Loading, Empty, List)
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)

        # 4a. Loading state
        loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        loading_box.set_valign(Gtk.Align.CENTER)
        loading_box.set_halign(Gtk.Align.CENTER)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.spinner.start()
        loading_box.append(self.spinner)

        self.loading_lbl = Gtk.Label(label="Scanning installed applications…")
        self.loading_lbl.add_css_class("dim-label")
        loading_box.append(self.loading_lbl)
        self.stack.add_named(loading_box, "loading")

        # 4b. Empty state
        self.empty_status = Adw.StatusPage()
        self.empty_status.set_icon_name("edit-find-symbolic")
        self.empty_status.set_title("No Applications Found")
        self.empty_status.set_description("Try clearing your search query or choosing a different filter.")
        self.stack.add_named(self.empty_status, "empty")

        # 4c. Scrolled List
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("navigation-sidebar")
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-selected", self._on_row_selected)
        self.scroller.set_child(self.list_box)
        self.stack.add_named(self.scroller, "list")

        self.append(self.stack)
        self.stack.set_visible_child_name("loading")

    def toggle_search(self) -> None:
        """Toggle search bar visibility and focus entry."""
        current = self.search_bar.get_search_mode()
        self.search_bar.set_search_mode(not current)
        if not current:
            self.search_entry.grab_focus()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._search_text = entry.get_text()
        self.refresh_list()

    def _on_filter_changed(self, dropdown: Gtk.DropDown, param) -> None:
        idx = dropdown.get_selected()
        if 0 <= idx < len(self.FILTER_ORDER):
            self._active_category = self.FILTER_ORDER[idx]
            self.refresh_list()

    def _on_sort_changed(self, dropdown: Gtk.DropDown, param) -> None:
        idx = dropdown.get_selected()
        mapping = {0: "name", 1: "source", 2: "scope", 3: "size"}
        self._sort_by = mapping.get(idx, "name")
        self.refresh_list()

    def _on_row_selected(self, listbox: Gtk.ListBox, row: Optional[Gtk.ListBoxRow]) -> None:
        if row and hasattr(row, "record"):
            self._on_select_record(row.record)

    def set_loading(self, is_loading: bool, message: str = "Scanning applications…") -> None:
        if is_loading:
            self.loading_lbl.set_label(message)
            self.spinner.start()
            self.stack.set_visible_child_name("loading")
        else:
            self.spinner.stop()

    def update_snapshot(self, snapshot: InventorySnapshot) -> None:
        """Update category counts and re-populate list."""
        # Update dropdown titles with real counts
        for i, cat in enumerate(self.FILTER_ORDER):
            count = snapshot.count_by_filter(cat)
            base_title = self._filter_strings[i].split(" (")[0]
            new_title = f"{base_title} ({count})"
            # Gtk.StringList splice or replace item
            self._string_list.splice(i, 1, [new_title])

        self.summary_lbl.set_label(f"{snapshot.total_count} applications discoverable across providers")
        self.refresh_list()

    def refresh_list(self) -> None:
        """Filter, sort, and render rows using native ActionRow style."""
        # Clear rows
        while True:
            row = self.list_box.get_row_at_index(0)
            if row is None:
                break
            self.list_box.remove(row)

        items = self._orchestrator.query(
            category=self._active_category,
            search_query=self._search_text,
            sort_by=self._sort_by,
            sort_ascending=self._sort_asc,
        )

        if not items:
            self.stack.set_visible_child_name("empty")
            return

        self.stack.set_visible_child_name("list")
        for record in items:
            row = Adw.ActionRow()
            row.record = record
            row.set_title(record.name)
            row.set_subtitle(record.package_id)

            # Icon prefix (32px)
            icon_name = record.icon_name_or_path or "application-x-executable-symbolic"
            img = Gtk.Image.new_from_icon_name(icon_name)
            img.set_pixel_size(32)
            img.set_valign(Gtk.Align.CENTER)
            row.add_prefix(img)

            # Plain muted suffix text: format and size (e.g., "Flatpak · 11.8 MB")
            suffix_parts = [record.source.value]
            if record.installed_size_bytes is not None:
                suffix_parts.append(format_bytes(record.installed_size_bytes))
            suffix_text = " · ".join(suffix_parts)

            suffix_lbl = Gtk.Label(label=suffix_text)
            suffix_lbl.add_css_class("caption")
            suffix_lbl.add_css_class("dim-label")
            suffix_lbl.add_css_class("numeric")
            suffix_lbl.set_valign(Gtk.Align.CENTER)
            row.add_suffix(suffix_lbl)

            self.list_box.append(row)
