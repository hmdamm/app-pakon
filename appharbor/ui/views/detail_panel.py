"""Application detail inspector conforming to GNOME HIG (Flatseal/GNOME Software style)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional
import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, Gio, Gtk, Adw, Pango

from appharbor.domain.models import InstallationRecord, ScopeEnum, SourceEnum
from appharbor.system.capabilities import format_bytes


class DetailPanel(Gtk.Box):
    """Right-hand panel inspecting application metadata, origins, and consequences."""

    def __init__(
        self,
        on_uninstall_requested: Callable[[InstallationRecord], None],
        on_toast: Optional[Callable[[str], None]] = None,
    ):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_vexpand(True)
        self.set_hexpand(True)

        self._on_uninstall_requested = on_uninstall_requested
        self._on_toast = on_toast
        self._current_record: Optional[InstallationRecord] = None

        # Contextual warning banner at top of inspector
        self.banner = Adw.Banner()
        self.banner.set_revealed(False)
        self.append(self.banner)

        # Scrolled container
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_vexpand(True)
        self.scroller.set_hexpand(True)

        # Clamp to enforce optimal GNOME reading width (720px)
        self.clamp = Adw.Clamp()
        self.clamp.set_maximum_size(720)
        self.clamp.set_tightening_threshold(560)
        self.clamp.set_margin_top(24)
        self.clamp.set_margin_bottom(32)
        self.clamp.set_margin_start(24)
        self.clamp.set_margin_end(24)

        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.clamp.set_child(self.content_box)
        self.scroller.set_child(self.clamp)

        # Stack between empty state and content view
        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)

        # Empty state status page
        self.status_page = Adw.StatusPage()
        self.status_page.set_icon_name("system-software-install-symbolic")
        self.status_page.set_title("No Application Selected")
        self.status_page.set_description("Select an application from the sidebar to inspect its details, files, and permissions.")
        self.status_page.set_vexpand(True)

        self.stack.add_named(self.status_page, "empty")
        self.stack.add_named(self.scroller, "content")
        self.append(self.stack)

        self.show_empty()

    def show_empty(self) -> None:
        """Render empty selection placeholder."""
        self.banner.set_revealed(False)
        self.stack.set_visible_child_name("empty")
        self._current_record = None

    def display_record(self, record: InstallationRecord) -> None:
        """Display metadata for an installation record in idiomatic GNOME cards."""
        self._current_record = record
        self._clear_content()

        # 1. Update Contextual Banner
        if record.is_critical_system_package:
            self.banner.set_title("Protected Core System Component. Uninstallation is blocked to preserve operating system integrity.")
            self.banner.set_revealed(True)
        elif record.requires_elevation:
            self.banner.set_title("System-Wide Package: Modifications will request administrator authorization via Polkit.")
            self.banner.set_revealed(True)
        else:
            self.banner.set_revealed(False)

        # 2. Hero App Header Card (Flatseal/GNOME Software style)
        hero_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        hero_card.set_margin_bottom(8)

        # Large 64px Icon
        icon_name = record.icon_name_or_path or "application-x-executable-symbolic"
        icon_img = Gtk.Image.new_from_icon_name(icon_name)
        icon_img.set_pixel_size(64)
        icon_img.set_valign(Gtk.Align.CENTER)
        hero_card.append(icon_img)

        # Title, ID, and Badges
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_box.set_hexpand(True)
        title_box.set_valign(Gtk.Align.CENTER)

        name_lbl = Gtk.Label(label=record.name)
        name_lbl.add_css_class("title-1")
        name_lbl.set_halign(Gtk.Align.START)
        name_lbl.set_wrap(True)
        name_lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        title_box.append(name_lbl)

        id_lbl = Gtk.Label(label=record.package_id)
        id_lbl.add_css_class("dim-label")
        id_lbl.add_css_class("monospace")
        id_lbl.set_halign(Gtk.Align.START)
        id_lbl.set_selectable(True)
        title_box.append(id_lbl)

        # Plain secondary metadata text separated by bullets
        meta_parts = [record.source.value, record.scope.value]
        if record.version:
            meta_parts.append(f"v{record.version}")
        meta_text = "  •  ".join(meta_parts)

        meta_lbl = Gtk.Label(label=meta_text)
        meta_lbl.add_css_class("caption")
        meta_lbl.add_css_class("dim-label")
        meta_lbl.set_halign(Gtk.Align.START)
        meta_lbl.set_valign(Gtk.Align.CENTER)
        meta_lbl.set_margin_top(2)
        title_box.append(meta_lbl)
        hero_card.append(title_box)

        # Hero Action Area (Uninstall button)
        action_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        action_area.set_valign(Gtk.Align.CENTER)
        action_area.set_halign(Gtk.Align.END)

        if record.is_removable and not record.is_critical_system_package:
            uninstall_btn = Gtk.Button(label="Uninstall…")
            uninstall_btn.add_css_class("destructive-action")
            uninstall_btn.add_css_class("pill")
            uninstall_btn.connect("clicked", lambda b: self._on_uninstall_requested(record))
            action_area.append(uninstall_btn)
        elif record.is_critical_system_package:
            lock_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            lock_box.add_css_class("dim-label")
            lock_icon = Gtk.Image.new_from_icon_name("changes-prevent-symbolic")
            lock_lbl = Gtk.Label(label="System Protected")
            lock_box.append(lock_icon)
            lock_box.append(lock_lbl)
            action_area.append(lock_box)

        hero_card.append(action_area)
        self.content_box.append(hero_card)

        # 3. Description (if available)
        if record.description:
            desc_group = Adw.PreferencesGroup()
            desc_group.set_title("About")
            desc_row = Adw.ActionRow()
            desc_row.set_title("Description")
            desc_row.set_subtitle(record.description)
            desc_row.set_subtitle_selectable(True)
            desc_group.add(desc_row)
            self.content_box.append(desc_group)

        # 4. Package & Provenance Details Group
        pkg_group = Adw.PreferencesGroup()
        pkg_group.set_title("Package Details")

        self._add_property_row(pkg_group, "Application ID", record.package_id, is_mono=True)
        self._add_property_row(pkg_group, "Packaging Source", record.source.value)
        self._add_property_row(pkg_group, "Installation Scope", record.scope.value)
        if record.version:
            self._add_property_row(pkg_group, "Version", record.version, is_numeric=True)
        if record.architecture:
            self._add_property_row(pkg_group, "Architecture", record.architecture)
        if record.installed_size_bytes is not None:
            self._add_property_row(pkg_group, "Installed Size", format_bytes(record.installed_size_bytes), is_numeric=True)
        if record.origin:
            self._add_property_row(pkg_group, "Origin / Repository", record.origin)

        self.content_box.append(pkg_group)

        # 5. Filesystem & Integration Group
        fs_group = Adw.PreferencesGroup()
        fs_group.set_title("Filesystem and Integration")

        if record.install_path:
            self._add_path_row(fs_group, "Installation Path", record.install_path)
        if record.desktop_entry_path:
            self._add_path_row(fs_group, "Desktop Launcher", record.desktop_entry_path)
        if record.exec_target:
            self._add_copyable_row(fs_group, "Launch Command", record.exec_target)

        self.content_box.append(fs_group)

        # 6. Safety & Removal Preview Group
        safety_group = Adw.PreferencesGroup()
        safety_group.set_title("Removal Plan Preview")

        auth_row = Adw.ActionRow()
        auth_row.set_title("Administrator Permission")
        auth_row.set_subtitle("Required (Polkit authorization)" if record.requires_elevation else "Not required (User-scoped)")
        auth_img = Gtk.Image.new_from_icon_name("dialog-password-symbolic" if record.requires_elevation else "avatar-default-symbolic")
        auth_row.add_prefix(auth_img)
        safety_group.add(auth_row)

        data_row = Adw.ActionRow()
        data_row.set_title("User Data Handling")
        data_row.set_subtitle("Preserved by default in home directory" if not record.is_critical_system_package else "N/A (System package)")
        data_img = Gtk.Image.new_from_icon_name("folder-documents-symbolic")
        data_row.add_prefix(data_img)
        safety_group.add(data_row)

        self.content_box.append(safety_group)

        self.stack.set_visible_child_name("content")

    def _add_property_row(
        self,
        group: Adw.PreferencesGroup,
        title: str,
        subtitle: str,
        is_mono: bool = False,
        is_numeric: bool = False,
    ) -> None:
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_subtitle_selectable(True)
        row.add_css_class("property")
        if is_mono:
            row.add_css_class("monospace")
        if is_numeric:
            row.add_css_class("numeric")
        group.add(row)

    def _add_path_row(self, group: Adw.PreferencesGroup, title: str, path_str: str) -> None:
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(path_str)
        row.set_subtitle_selectable(True)
        row.add_css_class("property")
        row.add_css_class("monospace")

        # Copy button
        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(f"Copy {title}")
        copy_btn.connect("clicked", lambda b: self._copy_to_clipboard(path_str, f"Copied {title}"))
        row.add_suffix(copy_btn)

        # Open containing folder button if path exists
        p = Path(path_str)
        target_dir = p.parent if p.is_file() else p
        if target_dir.exists():
            open_btn = Gtk.Button()
            open_btn.set_icon_name("folder-open-symbolic")
            open_btn.add_css_class("flat")
            open_btn.set_tooltip_text("Open Containing Folder")
            open_btn.connect("clicked", lambda b: self._open_folder(str(target_dir)))
            row.add_suffix(open_btn)

        group.add(row)

    def _add_copyable_row(self, group: Adw.PreferencesGroup, title: str, text: str) -> None:
        row = Adw.ActionRow()
        row.set_title(title)
        row.set_subtitle(text)
        row.set_subtitle_selectable(True)
        row.add_css_class("property")
        row.add_css_class("monospace")

        copy_btn = Gtk.Button()
        copy_btn.set_icon_name("edit-copy-symbolic")
        copy_btn.add_css_class("flat")
        copy_btn.set_tooltip_text(f"Copy {title}")
        copy_btn.connect("clicked", lambda b: self._copy_to_clipboard(text, f"Copied {title}"))
        row.add_suffix(copy_btn)

        group.add(row)

    def _copy_to_clipboard(self, text: str, toast_msg: str) -> None:
        display = Gdk.Display.get_default()
        if display:
            clipboard = display.get_clipboard()
            clipboard.set(text)
            if self._on_toast:
                self._on_toast(toast_msg)

    def _open_folder(self, folder_path: str) -> None:
        try:
            Gio.AppInfo.launch_default_for_uri(f"file://{folder_path}", None)
        except Exception:
            pass

    def _clear_content(self) -> None:
        while True:
            child = self.content_box.get_first_child()
            if child is None:
                break
            self.content_box.remove(child)
