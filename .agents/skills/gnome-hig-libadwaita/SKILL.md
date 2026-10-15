---
name: gnome-hig-libadwaita
description: "Guidelines and architecture rules for building native GNOME applications adhering strictly to GNOME Human Interface Guidelines (HIG) and Libadwaita patterns (inspired by GNOME Circle apps like Warehouse, Flatseal, and Cartridges). Prohibits web-style palette overrides and custom box soup."
---

# GNOME HIG & Libadwaita Development Skill

This skill enforces idiomatic, beautiful GNOME desktop application patterns using GTK4 and Libadwaita. It prevents web-style custom color overrides, fragile layouts ("box soup"), and unstandardized widgets.

## Core Rules & Non-Negotiables

### 1. Zero Custom Palette Overrides
- **Never** hardcode custom `#hex` color palettes, backgrounds, text colors, or borders in CSS.
- **Rely 100% on Libadwaita's native adaptive theme engine**, which automatically synchronizes with GNOME system dark and light modes.
- If subtle semantic coloring is needed, reference Libadwaita's built-in named colors with alpha blending:
  - `@accent_bg_color`, `@accent_fg_color`
  - `@warning_bg_color`, `@warning_fg_color`
  - `@error_bg_color`, `@error_fg_color`
  - `@card_bg_color`, `@card_fg_color`
  - `@window_bg_color`, `@window_fg_color`
  - `@view_bg_color`, `@view_fg_color`

### 2. Standard Libadwaita Style Classes
Always use built-in HIG style classes instead of custom CSS rules:
- **Typography:** `.title-1`, `.title-2`, `.title-3`, `.title-4`, `.heading`, `.body`, `.caption`, `.dim-label`
- **Data & Numbers:** `.numeric` (tabular figures), `.monospace` (code/package IDs/paths)
- **Container Styling:** `.boxed-list`, `.navigation-sidebar`, `.card`, `.property`
- **Buttons & Badges:** `.pill`, `.flat`, `.suggested-action`, `.destructive-action`, `.opaque`

### 3. Semantic Libadwaita Containers
Avoid composing layouts from generic nested `Gtk.Box` widgets ("box soup"). Prefer high-level semantic Libadwaita widgets:
- `Adw.NavigationSplitView`: Standard responsive master-detail pattern (sidebar list + detail pane). Automatically manages adaptive collapsing on smaller screens.
- `Adw.ToolbarView`: Manages top/bottom toolbars, header bars, and scrolling view boundaries cleanly.
- `Adw.HeaderBar`: Standard window titlebar supporting search toggles, window controls, and action buttons.
- `Adw.Clamp`: Constrains wide views (e.g. details page, forms) to optimal readable widths (`maximum_size=720` or `800`).
- `Adw.PreferencesPage` & `Adw.PreferencesGroup`: Clean, grouped settings and metadata cards with standardized margins and headers.
- `Adw.ActionRow` & `Adw.ExpanderRow`: The gold standard for metadata and interactive items, with `.title`, `.subtitle`, prefix icons, and suffix widgets.
- `Adw.StatusPage`: Dedicated empty, loading, or error state screen with standardized iconography and descriptions.
- `Adw.Banner`: Native contextual message bar for elevation warnings or critical component alerts.
- `Adw.AlertDialog` / `Adw.MessageDialog`: Standard modal dialogs for destructive confirmations.

### 4. Inspiration & Reference Apps
- **Flatseal:** Master-detail list of applications on the left sidebar, clean permission cards and metadata groups with switches and badges on the right.
- **Warehouse:** Clean package and runtime management with search, filter popover/dropdown, and safe removal with user data management.
- **Cartridges:** Polished game library launcher with native action rows, clean detail pages, and smooth search.
