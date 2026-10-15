"""Safe uninstallation confirmation dialog."""

from __future__ import annotations

from typing import Callable, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from appharbor.domain.models import InstallationRecord, UninstallPlan


class SafeUninstallDialog(Adw.Window):
    """Modal dialog presenting explicit uninstallation consequences before action."""

    def __init__(
        self,
        parent: Gtk.Window,
        record: InstallationRecord,
        plan: UninstallPlan,
        on_confirm: Callable[[bool], None],
    ):
        super().__init__()
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_title("Confirm Uninstallation")
        self.set_default_size(460, -1)
        self.set_resizable(False)

        self._record = record
        self._plan = plan
        self._on_confirm = on_confirm

        self._build_ui()

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        main_box.set_margin_top(24)
        main_box.set_margin_bottom(24)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)

        # Header Icon & Title
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        icon = Gtk.Image.new_from_icon_name(self._record.icon_name_or_path or "application-x-executable")
        icon.set_pixel_size(48)
        header_box.append(icon)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_lbl = Gtk.Label(label=f"Uninstall {self._record.name}?")
        title_lbl.add_css_class("detail-title")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.set_ellipsize(Pango.EllipsizeMode.END)

        pkg_lbl = Gtk.Label(label=f"Package ID: {self._record.package_id}")
        pkg_lbl.add_css_class("detail-package-id")
        pkg_lbl.set_halign(Gtk.Align.START)

        title_box.append(title_lbl)
        title_box.append(pkg_lbl)
        header_box.append(title_box)
        main_box.append(header_box)

        # Details list group
        group = Adw.PreferencesGroup()
        group.set_title("Package Details")

        row_src = Adw.ActionRow()
        row_src.set_title("Installation Source")
        row_src.set_subtitle(self._record.source.value)
        group.add(row_src)

        row_scope = Adw.ActionRow()
        row_scope.set_title("Installation Scope")
        row_scope.set_subtitle(self._record.scope.value)
        group.add(row_scope)

        if self._record.install_path:
            row_path = Adw.ActionRow()
            row_path.set_title("Installation Path")
            row_path.set_subtitle(self._record.install_path)
            group.add(row_path)

        main_box.append(group)

        # Elevation warning if applicable
        if self._plan.requires_elevation:
            elev_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            elev_box.add_css_class("warning-box")
            elev_icon = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
            elev_lbl = Gtk.Label(
                label="Administrator authorization (Polkit) will be requested by the system to remove this package."
            )
            elev_lbl.set_wrap(True)
            elev_box.append(elev_icon)
            elev_box.append(elev_lbl)
            main_box.append(elev_box)

        # Personal data handling checkbox
        data_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.data_check = Gtk.CheckButton(label="Also delete user settings and personal data")
        self.data_check.set_active(False)  # Default: PRESERVE DATA!

        data_desc = Gtk.Label(
            label="By default, personal configuration files in your home directory are preserved."
        )
        data_desc.add_css_class("app-subtitle")
        data_desc.set_wrap(True)
        data_desc.set_halign(Gtk.Align.START)

        data_box.append(self.data_check)
        data_box.append(data_desc)

        if self._plan.user_data_paths:
            path_lbl = Gtk.Label(label=f"Identified path: {self._plan.user_data_paths[0]}")
            path_lbl.add_css_class("detail-prop-mono")
            path_lbl.set_halign(Gtk.Align.START)
            data_box.append(path_lbl)

        main_box.append(data_box)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.END)
        btn_box.set_margin_top(8)

        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())

        uninstall_btn = Gtk.Button(label="Uninstall Application")
        uninstall_btn.add_css_class("btn-destructive")
        uninstall_btn.connect("clicked", self._on_uninstall_clicked)

        btn_box.append(cancel_btn)
        btn_box.append(uninstall_btn)
        main_box.append(btn_box)

        self.set_content(main_box)

    def _on_uninstall_clicked(self, btn: Gtk.Button) -> None:
        keep_data = not self.data_check.get_active()
        self.close()
        self._on_confirm(keep_data)
