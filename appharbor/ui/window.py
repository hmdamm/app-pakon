"""Main application window for AppHarbor."""

from __future__ import annotations

import logging
import threading
from typing import Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from appharbor import __version__
from appharbor.domain.models import InstallationRecord, OperationResult
from appharbor.inventory.orchestrator import InventoryOrchestrator, InventorySnapshot
from appharbor.ui.tokens import load_custom_css
from appharbor.ui.views.detail_panel import DetailPanel
from appharbor.ui.views.dialogs import SafeUninstallDialog
from appharbor.ui.views.inventory_view import InventoryView
from appharbor.uninstall.service import UninstallService

logger = logging.getLogger(__name__)


class AppHarborWindow(Adw.ApplicationWindow):
    """Main window with master-detail navigation split view."""

    def __init__(self, app: Adw.Application, orchestrator: InventoryOrchestrator):
        super().__init__(application=app)
        self.set_title("AppHarbor")
        self.set_default_size(1120, 740)
        self.set_size_request(800, 520)
        self.add_css_class("appharbor-window")

        self._orchestrator = orchestrator
        self._uninstall_service = UninstallService(orchestrator)
        self._is_scanning = False

        load_custom_css()
        self._build_ui()
        self.start_background_scan()

    def _build_ui(self) -> None:
        toolbar_view = Adw.ToolbarView()

        # 1. HeaderBar
        header_bar = Adw.HeaderBar()
        header_bar.add_css_class("appharbor-headerbar")

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        title_box.set_valign(Gtk.Align.CENTER)
        app_title = Gtk.Label(label="AppHarbor")
        app_title.add_css_class("app-title")
        app_sub = Gtk.Label(label="Universal Linux Application Manager")
        app_sub.add_css_class("app-subtitle")
        title_box.append(app_title)
        title_box.append(app_sub)
        header_bar.set_title_widget(title_box)

        # Refresh / Rescan button
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_icon_name("view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text("Rescan all installed applications")
        self.refresh_btn.connect("clicked", lambda b: self.start_background_scan())
        header_bar.pack_start(self.refresh_btn)

        # About button
        about_btn = Gtk.Button()
        about_btn.set_icon_name("help-about-symbolic")
        about_btn.set_tooltip_text("About AppHarbor")
        about_btn.connect("clicked", self._on_about_clicked)
        header_bar.pack_end(about_btn)

        toolbar_view.add_top_bar(header_bar)

        # 2. Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()

        # 3. Master-Detail Paned Split
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(580)
        paned.set_wide_handle(True)

        # Left: Inventory Explorer
        self.inventory_view = InventoryView(
            orchestrator=self._orchestrator,
            on_select_record=self._on_record_selected,
        )
        paned.set_start_child(self.inventory_view)

        # Right: Detail Inspection Panel
        self.detail_panel = DetailPanel(
            on_uninstall_requested=self._on_uninstall_requested,
        )
        paned.set_end_child(self.detail_panel)

        self.toast_overlay.set_child(paned)
        toolbar_view.set_content(self.toast_overlay)
        self.set_content(toolbar_view)

    def _on_record_selected(self, record: InstallationRecord) -> None:
        self.detail_panel.display_record(record)

    def _on_uninstall_requested(self, record: InstallationRecord) -> None:
        # Generate initial plan
        plan = self._uninstall_service.create_uninstall_plan(record, keep_data=True)
        if not plan.is_executable:
            self.show_toast(plan.error_message or "Uninstallation is not permitted.")
            return

        dialog = SafeUninstallDialog(
            parent=self,
            record=record,
            plan=plan,
            on_confirm=lambda keep_data: self._execute_uninstall(record, keep_data),
        )
        dialog.present()

    def _execute_uninstall(self, record: InstallationRecord, keep_data: bool) -> None:
        plan = self._uninstall_service.create_uninstall_plan(record, keep_data=keep_data)
        self.show_toast(f"Uninstalling {record.name}...")

        def _worker():
            res: OperationResult = self._uninstall_service.execute_plan(plan)
            GLib.idle_add(self._on_uninstall_finished, res)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_uninstall_finished(self, result: OperationResult) -> None:
        if result.success:
            self.show_toast(f"✓ {result.message}")
            self.detail_panel.show_empty()
            self.start_background_scan()
        else:
            self.show_toast(f"❌ {result.message}")

    def start_background_scan(self) -> None:
        if self._is_scanning:
            return
        self._is_scanning = True
        self.refresh_btn.set_sensitive(False)
        self.inventory_view.set_scanning_progress("Scanning applications...", 0.1)

        def _progress(msg: str, frac: float):
            GLib.idle_add(self.inventory_view.set_scanning_progress, msg, frac)

        def _worker():
            snapshot = self._orchestrator.scan_all(progress_callback=_progress)
            GLib.idle_add(self._on_scan_finished, snapshot)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_finished(self, snapshot: InventorySnapshot) -> None:
        self._is_scanning = False
        self.refresh_btn.set_sensitive(True)
        self.inventory_view.set_scanning_progress("Done", 1.0)
        self.inventory_view.update_snapshot(snapshot)

        self.show_toast(f"Discovered {snapshot.total_count} installed applications.")

    def show_toast(self, text: str) -> None:
        toast = Adw.Toast(title=text)
        toast.set_timeout(4)
        self.toast_overlay.add_toast(toast)

    def _on_about_clicked(self, btn: Gtk.Button) -> None:
        dialog = Adw.AboutWindow()
        dialog.set_transient_for(self)
        dialog.set_application_name("AppHarbor")
        dialog.set_application_icon("system-software-install")
        dialog.set_developer_name("Open Source Contributors")
        dialog.set_version(__version__)
        dialog.set_website("https://github.com/appharbor/appharbor")
        dialog.set_issue_url("https://github.com/appharbor/appharbor/issues")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_comments(
            "A polished, trustworthy desktop application for Linux that unifies application discovery, "
            "provenance inspection, and safe uninstallation across Flatpak, RPM, Snap, AppImage, and manual installations."
        )
        dialog.present()
