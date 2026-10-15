"""Safe uninstallation confirmation dialog conforming to GNOME HIG."""

from __future__ import annotations

from typing import Callable, Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Pango

from appharbor.domain.models import InstallationRecord, UninstallPlan


def show_safe_uninstall_dialog(
    parent: Gtk.Widget,
    record: InstallationRecord,
    plan: UninstallPlan,
    on_confirm: Callable[[bool], None],
) -> Adw.AlertDialog:
    """Display an idiomatic Adw.AlertDialog with destructive styling and explicit data options."""
    dialog = Adw.AlertDialog(
        heading=f"Uninstall {record.name}?",
        body=(
            f"Are you sure you want to remove this application package?\n"
            f"Package: {record.package_id} · Source: {record.source.value} · Scope: {record.scope.value}"
        ),
    )

    dialog.add_response("cancel", "Cancel")
    dialog.add_response("uninstall", "Uninstall")
    dialog.set_response_appearance("uninstall", Adw.ResponseAppearance.DESTRUCTIVE)
    dialog.set_default_response("cancel")
    dialog.set_close_response("cancel")

    # Extra options in a clean PreferencesGroup
    group = Adw.PreferencesGroup()

    # Elevation notice if applicable
    if plan.requires_elevation:
        elev_row = Adw.ActionRow()
        elev_row.set_title("Administrator Authorization Required")
        elev_row.set_subtitle("System authorization (Polkit) will be requested to complete this action.")
        img = Gtk.Image.new_from_icon_name("dialog-password-symbolic")
        elev_row.add_prefix(img)
        group.add(elev_row)

    # Personal data switch row (default OFF to preserve data)
    switch_row = Adw.SwitchRow()
    switch_row.set_title("Delete Personal Data and User Settings")
    switch_row.set_subtitle("Default is OFF to keep application data in your home directory")
    switch_row.set_active(False)
    group.add(switch_row)

    # Command preview row
    if plan.commands_to_run:
        cmd_row = Adw.ActionRow()
        cmd_row.set_title("Command to Execute")
        cmd_str = " ".join(plan.commands_to_run[0])
        cmd_row.set_subtitle(cmd_str)
        cmd_row.add_css_class("property")
        cmd_row.set_subtitle_selectable(True)
        img_term = Gtk.Image.new_from_icon_name("utilities-terminal-symbolic")
        cmd_row.add_prefix(img_term)
        group.add(cmd_row)

    dialog.set_extra_child(group)

    def _on_response(dlg: Adw.AlertDialog, response_id: str) -> None:
        if response_id == "uninstall":
            keep_data = not switch_row.get_active()
            on_confirm(keep_data)

    dialog.connect("response", _on_response)
    dialog.present(parent)
    return dialog


class SafeUninstallDialog:
    """Backwards compatibility shim for existing call sites."""

    def __init__(
        self,
        parent: Gtk.Widget,
        record: InstallationRecord,
        plan: UninstallPlan,
        on_confirm: Callable[[bool], None],
    ):
        self._dialog = show_safe_uninstall_dialog(parent, record, plan, on_confirm)

    def present(self) -> None:
        pass
