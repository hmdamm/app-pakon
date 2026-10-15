"""Inventory view with filter pills, search bar, and scannable list."""

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
from appharbor.ui.tokens import create_chip


class InventoryRow(Gtk.ListBoxRow):
    """Row representing a single application installation."""

    def __init__(self, record: InstallationRecord):
        super().__init__()
        self.record = record
        self.add_css_class("app-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        # App Icon
        icon_name = record.icon_name_or_path or "application-x-executable"
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(40)
        box.append(icon)

        # Title & ID column
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        text_box.set_hexpand(True)

        top_line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        name_lbl = Gtk.Label(label=record.name)
        name_lbl.add_css_class("app-row-name")
        name_lbl.set_halign(Gtk.Align.START)
        top_line.append(name_lbl)

        if record.version:
            ver_lbl = Gtk.Label(label=f"v{record.version}")
            ver_lbl.add_css_class("app-row-version")
            top_line.append(ver_lbl)

        text_box.append(top_line)

        pkg_lbl = Gtk.Label(label=record.package_id)
        pkg_lbl.add_css_class("app-row-id")
        pkg_lbl.set_halign(Gtk.Align.START)
        pkg_lbl.set_ellipsize(Pango.EllipsizeMode.END)
        text_box.append(pkg_lbl)

        box.append(text_box)

        # Right side: Size and Badges
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        right_box.set_valign(Gtk.Align.CENTER)

        if record.installed_size_bytes is not None:
            size_lbl = Gtk.Label(label=format_bytes(record.installed_size_bytes))
            size_lbl.add_css_class("app-row-size")
            right_box.append(size_lbl)

        # Source chip
        src_class = f"chip-{record.source.value.lower().replace('/', '')}"
        right_box.append(create_chip(record.source.value, src_class))

        # Scope chip
        scope_class = "chip-user" if record.scope == ScopeEnum.USER else "chip-system"
        right_box.append(create_chip(record.scope.value, scope_class))

        box.append(right_box)
        self.set_child(box)


class InventoryView(Gtk.Box):
    """Main inventory explorer containing search, category pills, and application list."""

    def __init__(
        self,
        orchestrator: InventoryOrchestrator,
        on_select_record: Callable[[InstallationRecord], None],
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self._orchestrator = orchestrator
        self._on_select_record = on_select_record
        self._active_category = FilterCategory.ALL
        self._search_text = ""
        self._sort_by = "name"
        self._sort_asc = True

        self._pill_buttons: dict[FilterCategory, Gtk.Button] = {}
        self._pill_count_labels: dict[FilterCategory, Gtk.Label] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Search Bar & Sort Dropdown
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        search_box.add_css_class("search-container")

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search applications by name, package ID, or keyword...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.append(self.search_entry)

        # Sort Dropdown
        sort_model = Gtk.StringList.new(["Sort: Name (A-Z)", "Sort: Source", "Sort: Scope", "Sort: Size"])
        self.sort_dropdown = Gtk.DropDown(model=sort_model)
        self.sort_dropdown.connect("notify::selected", self._on_sort_changed)
        search_box.append(self.sort_dropdown)

        self.append(search_box)

        # 2. Filter Pills Scroller
        pills_scroll = Gtk.ScrolledWindow()
        pills_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        pills_scroll.set_min_content_height(48)
        pills_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        pills_box.add_css_class("filter-bar")

        for cat in FilterCategory:
            btn = Gtk.Button()
            btn.add_css_class("filter-pill")
            if cat == self._active_category:
                btn.add_css_class("active")

            btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            lbl = Gtk.Label(label=cat.value)
            count_lbl = Gtk.Label(label="0")
            count_lbl.add_css_class("filter-count")

            btn_box.append(lbl)
            btn_box.append(count_lbl)
            btn.set_child(btn_box)

            btn.connect("clicked", self._make_pill_handler(cat))
            pills_box.append(btn)

            self._pill_buttons[cat] = btn
            self._pill_count_labels[cat] = count_lbl

        pills_scroll.set_child(pills_box)
        self.append(pills_scroll)

        # 3. Progress Bar (hidden by default)
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_visible(False)
        self.append(self.progress_bar)

        # 4. Applications List Container
        self.list_scroller = Gtk.ScrolledWindow()
        self.list_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_scroller.set_vexpand(True)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-selected", self._on_row_selected)

        self.empty_status = Adw.StatusPage()
        self.empty_status.set_icon_name("edit-find-symbolic")
        self.empty_status.set_title("No Applications Found")
        self.empty_status.set_description("Try clearing the search query or selecting a different filter.")
        self.empty_status.set_visible(False)
        self.empty_status.set_vexpand(True)

        stack = Gtk.Stack()
        stack.add_named(self.list_box, "list")
        stack.add_named(self.empty_status, "empty")
        self.stack = stack

        self.list_scroller.set_child(stack)
        self.append(self.list_scroller)

    def _make_pill_handler(self, cat: FilterCategory):
        def _handler(btn: Gtk.Button):
            for c, b in self._pill_buttons.items():
                b.remove_css_class("active")
            btn.add_css_class("active")
            self._active_category = cat
            self.refresh_list()
        return _handler

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._search_text = entry.get_text()
        self.refresh_list()

    def _on_sort_changed(self, dropdown: Gtk.DropDown, param) -> None:
        idx = dropdown.get_selected()
        mapping = {0: "name", 1: "source", 2: "scope", 3: "size"}
        self._sort_by = mapping.get(idx, "name")
        self.refresh_list()

    def _on_row_selected(self, listbox: Gtk.ListBox, row: Optional[InventoryRow]) -> None:
        if row and isinstance(row, InventoryRow):
            self._on_select_record(row.record)

    def update_snapshot(self, snapshot: InventorySnapshot) -> None:
        """Update category count badges and populate list."""
        for cat in FilterCategory:
            count = snapshot.count_by_filter(cat)
            if cat in self._pill_count_labels:
                self._pill_count_labels[cat].set_label(str(count))

        self.refresh_list()

    def refresh_list(self) -> None:
        """Filter, sort, and render rows."""
        # Clear existing rows
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
            row = InventoryRow(record)
            self.list_box.append(row)

    def set_scanning_progress(self, message: str, fraction: float) -> None:
        """Update progress bar during background scan."""
        if fraction < 1.0:
            self.progress_bar.set_visible(True)
            self.progress_bar.set_fraction(fraction)
            self.progress_bar.set_tooltip_text(message)
        else:
            self.progress_bar.set_visible(False)
