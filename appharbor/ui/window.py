"""Main application window for AppHarbor conforming to GNOME HIG."""

from __future__ import annotations

import logging
import threading
from typing import Optional
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib, Gio

from appharbor import __version__
from appharbor.domain.models import InstallationRecord, OperationResult
from appharbor.inventory.orchestrator import InventoryOrchestrator, InventorySnapshot
from appharbor.ui.tokens import load_custom_css
from appharbor.ui.views.detail_panel import DetailPanel
from appharbor.ui.views.dialogs import show_safe_uninstall_dialog
from appharbor.ui.views.inventory_view import InventoryView
from appharbor.uninstall.service import UninstallService

logger = logging.getLogger(__name__)


class AppHarborWindow(Adw.ApplicationWindow):
    """Main window with native GNOME Adw.NavigationSplitView master-detail layout."""

    def __init__(self, app: Adw.Application, orchestrator: InventoryOrchestrator):
        super().__init__(application=app)
        self.set_title("AppHarbor")
        self.set_default_size(1080, 700)
        self.set_size_request(760, 480)

        self._orchestrator = orchestrator
        self._uninstall_service = UninstallService(orchestrator)
        self._is_scanning = False

        load_custom_css()
        self._build_ui()
        self._setup_shortcuts()
        self.start_background_scan()

    def _build_ui(self) -> None:
        # Root Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()

        # Split View
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_min_sidebar_width(340)
        self.split_view.set_max_sidebar_width(460)

        # === 1. Sidebar Page ===
        sidebar_toolbar = Adw.ToolbarView()

        sidebar_header = Adw.HeaderBar()
        sidebar_header.set_show_title(True)

        # Rescan / Refresh button
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_icon_name("view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text("Rescan installed applications (Ctrl+R)")
        self.refresh_btn.connect("clicked", lambda b: self.start_background_scan())
        sidebar_header.pack_start(self.refresh_btn)

        # Search toggle button
        self.search_btn = Gtk.Button()
        self.search_btn.set_icon_name("edit-find-symbolic")
        self.search_btn.set_tooltip_text("Search applications (Ctrl+F)")
        self.search_btn.connect("clicked", lambda b: self.inventory_view.toggle_search())
        sidebar_header.pack_end(self.search_btn)

        # About button
        about_btn = Gtk.Button()
        about_btn.set_icon_name("help-about-symbolic")
        about_btn.set_tooltip_text("About AppHarbor")
        about_btn.connect("clicked", self._on_about_clicked)
        sidebar_header.pack_end(about_btn)

        sidebar_toolbar.add_top_bar(sidebar_header)

        # Inventory Sidebar View
        self.inventory_view = InventoryView(
            orchestrator=self._orchestrator,
            on_select_record=self._on_record_selected,
            on_rescan_requested=self.start_background_scan,
        )
        sidebar_toolbar.set_content(self.inventory_view)

        sidebar_page = Adw.NavigationPage.new(sidebar_toolbar, "sidebar")
        sidebar_page.set_title("Applications")
        self.split_view.set_sidebar(sidebar_page)

        # === 2. Content Page ===
        content_toolbar = Adw.ToolbarView()

        content_header = Adw.HeaderBar()
        content_header.set_show_title(True)
        content_toolbar.add_top_bar(content_header)

        # Detail Inspection View
        self.detail_panel = DetailPanel(
            on_uninstall_requested=self._on_uninstall_requested,
            on_toast=self.show_toast,
        )
        content_toolbar.set_content(self.detail_panel)

        content_page = Adw.NavigationPage.new(content_toolbar, "content")
        content_page.set_title("Details")
        self.split_view.set_content(content_page)

        self.toast_overlay.set_child(self.split_view)
        self.set_content(self.toast_overlay)

    def _setup_shortcuts(self) -> None:
        """Register standard desktop keyboard shortcuts."""
        # Ctrl+F: Search
        action_find = Gio.SimpleAction.new("find", None)
        action_find.connect("activate", lambda a, p: self.inventory_view.toggle_search())
        self.add_action(action_find)

        # Ctrl+R: Refresh
        action_refresh = Gio.SimpleAction.new("refresh", None)
        action_refresh.connect("activate", lambda a, p: self.start_background_scan())
        self.add_action(action_refresh)

        # Bind accelerators
        app = self.get_application()
        if app:
            app.set_accels_for_action("win.find", ["<Control>f"])
            app.set_accels_for_action("win.refresh", ["<Control>r"])

    def _on_record_selected(self, record: InstallationRecord) -> None:
        self.detail_panel.display_record(record)
        # On narrow or collapsed view, navigate to content page
        self.split_view.set_show_content(True)

    def _on_uninstall_requested(self, record: InstallationRecord) -> None:
        plan = self._uninstall_service.create_uninstall_plan(record, keep_data=True)
        if not plan.is_executable:
            self.show_toast(plan.error_message or "Uninstallation is not permitted.")
            return

        show_safe_uninstall_dialog(
            parent=self,
            record=record,
            plan=plan,
            on_confirm=lambda keep_data: self._execute_uninstall(record, keep_data),
        )

    def _execute_uninstall(self, record: InstallationRecord, keep_data: bool) -> None:
        plan = self._uninstall_service.create_uninstall_plan(record, keep_data=keep_data)
        self.show_toast(f"Uninstalling {record.name}…")

        def _worker():
            res: OperationResult = self._uninstall_service.execute_plan(plan)
            GLib.idle_add(self._on_uninstall_finished, res)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_uninstall_finished(self, result: OperationResult) -> None:
        if result.success:
            self.show_toast(f"Removed {result.target_id}")
            self.detail_panel.show_empty()
            self.start_background_scan()
        else:
            self.show_toast(f"Error: {result.message}")

    def start_background_scan(self) -> None:
        if self._is_scanning:
            return
        self._is_scanning = True
        self.refresh_btn.set_sensitive(False)
        self.inventory_view.set_loading(True, "Scanning installed applications…")

        def _progress(msg: str, frac: float):
            pass

        def _worker():
            snapshot = self._orchestrator.scan_all(progress_callback=_progress)
            GLib.idle_add(self._on_scan_finished, snapshot)

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_finished(self, snapshot: InventorySnapshot) -> None:
        self._is_scanning = False
        self.refresh_btn.set_sensitive(True)
        self.inventory_view.set_loading(False)
        self.inventory_view.update_snapshot(snapshot)

        self.show_toast(f"{snapshot.total_count} applications discoverable")

    def show_toast(self, text: str) -> None:
        toast = Adw.Toast(title=text)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _on_about_clicked(self, btn: Gtk.Button) -> None:
        dialog = Adw.AboutWindow()
        dialog.set_transient_for(self)
        dialog.set_application_name("AppHarbor")
        dialog.set_application_icon("system-software-install-symbolic")
        dialog.set_developer_name("AppHarbor Team")
        dialog.set_version(__version__)
        dialog.set_website("https://github.com/hmdamm/app-pakon")
        dialog.set_issue_url("https://github.com/hmdamm/app-pakon/issues")
        dialog.set_license_type(Gtk.License.MIT_X11)
        dialog.set_comments(
            "A native GNOME application to discover, inspect, and safely remove "
            "applications across Flatpak, RPM/DNF, Snap, AppImage, and manual installations."
        )
        dialog.present()
