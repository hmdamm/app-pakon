#!/usr/bin/env python3
"""Capture a native screenshot of AppHarbor for documentation and releases."""

import os
import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

from appharbor.inventory.orchestrator import InventoryOrchestrator
from appharbor.ui.window import AppHarborWindow


class ScreenshotCaptureApp(Adw.Application):
    def __init__(self, output_path: str):
        super().__init__(application_id="io.github.appharbor.AppHarbor.ScreenshotCapture")
        self.output_path = output_path
        self.orchestrator = InventoryOrchestrator()
        self.window = None

    def do_activate(self):
        self.window = AppHarborWindow(self, self.orchestrator)
        self.window.set_default_size(1120, 720)
        self.window.present()

        def check_and_capture():
            rows = []
            row = self.window.inventory_view.list_box.get_first_child()
            while row:
                rows.append(row)
                row = row.get_next_sibling()

            if not rows and self.window._is_scanning:
                return True

            target_row = rows[0] if rows else None
            for r in rows:
                rec = getattr(r, "_appharbor_record", None)
                if rec and "amberol" in rec.name.lower():
                    target_row = r
                    break

            if target_row:
                self.window.inventory_view.list_box.select_row(target_row)
                rec = getattr(target_row, "_appharbor_record", None)
                if rec:
                    self.window._on_record_selected(rec)

            def do_save():
                w = self.window.get_width()
                h = self.window.get_height()
                paintable = Gtk.WidgetPaintable.new(self.window)
                snap = Gtk.Snapshot()
                paintable.snapshot(snap, w, h)
                node = snap.to_node()
                native = self.window.get_native()
                renderer = native.get_renderer()
                texture = renderer.render_texture(node, None)
                os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                texture.save_to_png(self.output_path)
                print(f"Screenshot saved to: {self.output_path} ({w}x{h})")
                self.quit()
                return False

            GLib.timeout_add(800, do_save)
            return False

        GLib.timeout_add(1500, check_and_capture)


def main():
    target = os.path.abspath(
        sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots/appharbor-main.png"
    )
    app = ScreenshotCaptureApp(target)
    sys.exit(app.run(None))


if __name__ == "__main__":
    main()
