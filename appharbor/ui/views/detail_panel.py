"""Detail inspection panel for selected application."""

from __future__ import annotations

from typing import Callable, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from appharbor.domain.models import InstallationRecord, ScopeEnum, SourceEnum
from appharbor.system.capabilities import format_bytes
from appharbor.ui.tokens import create_chip


class DetailPanel(Gtk.ScrolledWindow):
    """Right-hand panel inspecting application metadata, origins, and consequences."""

    def __init__(self, on_uninstall_requested: Callable[[InstallationRecord], None]):
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self._on_uninstall_requested = on_uninstall_requested
        self._current_record: Optional[InstallationRecord] = None

        self._container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._container.add_css_class("detail-panel")
        self.set_child(self._container)

        self.show_empty()

    def show_empty(self) -> None:
        """Render empty selection placeholder."""
        self._clear_container()
        status_page = Adw.StatusPage()
        status_page.set_icon_name("application-x-executable-symbolic")
        status_page.set_title("No Application Selected")
        status_page.set_description("Select an application from the inventory to view its provenance and installation details.")
        status_page.set_vexpand(True)
        self._container.append(status_page)

    def display_record(self, record: InstallationRecord) -> None:
        """Display metadata for an installation record."""
        self._current_record = record
        self._clear_container()

        # Header Card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        card.add_css_class("detail-header-card")

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        icon = Gtk.Image.new_from_icon_name(record.icon_name_or_path or "application-x-executable")
        icon.set_pixel_size(56)
        top_row.append(icon)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        name_lbl = Gtk.Label(label=record.name)
        name_lbl.add_css_class("detail-title")
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_wrap(True)

        pkg_lbl = Gtk.Label(label=record.package_id)
        pkg_lbl.add_css_class("detail-package-id")
        pkg_lbl.set_halign(Gtk.Align.START)

        title_box.append(name_lbl)
        title_box.append(pkg_lbl)
        top_row.append(title_box)
        card.append(top_row)

        # Chips row
        chips_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        chips_box.set_margin_top(4)

        # Source chip
        src_class = f"chip-{record.source.value.lower().replace('/', '')}"
        chips_box.append(create_chip(record.source.value, src_class))

        # Scope chip
        scope_class = "chip-user" if record.scope == ScopeEnum.USER else "chip-system"
        chips_box.append(create_chip(record.scope.value, scope_class))

        if record.version:
            ver_lbl = Gtk.Label(label=f"v{record.version}")
            ver_lbl.add_css_class("app-row-version")
            chips_box.append(ver_lbl)

        card.append(chips_box)
        self._container.append(card)

        # Warning boxes if critical or duplicate
        if record.is_critical_system_package:
            crit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            crit_box.add_css_class("critical-box")
            crit_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
            crit_lbl = Gtk.Label(
                label="Protected Core System Component: Uninstallation is disabled to protect your operating system."
            )
            crit_lbl.set_wrap(True)
            crit_box.append(crit_icon)
            crit_box.append(crit_lbl)
            self._container.append(crit_box)

        for w in record.warnings:
            w_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            w_box.add_css_class("warning-box")
            w_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
            w_lbl = Gtk.Label(label=w)
            w_lbl.set_wrap(True)
            w_box.append(w_icon)
            w_box.append(w_lbl)
            self._container.append(w_box)

        # Metadata Details Group
        pref_group = Adw.PreferencesGroup()
        pref_group.set_title("Properties & Location")

        self._add_action_row(pref_group, "Origin / Repository", record.origin or "Local system")
        self._add_action_row(pref_group, "Installed Size", format_bytes(record.installed_size_bytes))
        if record.architecture:
            self._add_action_row(pref_group, "Architecture", record.architecture)
        if record.install_path:
            self._add_action_row(pref_group, "Installation Path", record.install_path)
        if record.exec_target:
            self._add_action_row(pref_group, "Launch Target", record.exec_target)
        if record.desktop_entry_path:
            self._add_action_row(pref_group, "Desktop Launcher", record.desktop_entry_path)

        self._container.append(pref_group)

        # Actions section
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        action_box.set_margin_top(16)
        action_box.set_halign(Gtk.Align.END)

        if record.is_removable and not record.is_critical_system_package:
            uninstall_btn = Gtk.Button(label="Uninstall Application...")
            uninstall_btn.add_css_class("btn-destructive")
            uninstall_btn.connect("clicked", lambda b: self._on_uninstall_requested(record))
            action_box.append(uninstall_btn)
        elif record.is_critical_system_package:
            disabled_btn = Gtk.Button(label="System Protected")
            disabled_btn.set_sensitive(False)
            action_box.append(disabled_btn)

        self._container.append(action_box)

    def _add_action_row(self, group: Adw.PreferencesGroup, title: str, subtitle: str) -> None:
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_subtitle_selectable(True)
        group.add(row)

    def _clear_container(self) -> None:
        while True:
            child = self._container.get_first_child()
            if child is None:
                break
            self._container.remove(child)
