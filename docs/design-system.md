# Design System Specification — AppHarbor

**Design System:** AppHarbor Minimal Swiss & Warm Graphite  
**Generated via:** UI/UX Pro Max (`uipro`) Intelligence Engine  
**Target:** Linux Desktop (GTK4 / Libadwaita / AdwStyleManager)

---

## 1. Visual Direction & Color Palette

In accordance with Section 2 and Section 9 of the implementation plan, the visual direction deliberately departs from the generic blue/purple SaaS look. It implements a warm, tactile, high-contrast palette combining **warm graphite & ivory** surfaces with **restrained amber, terracotta, and lime** semantic accents.

### 1.1 Color Tokens

#### Dark Theme (Default on modern developer workstations)
| Token Name | Hex Code | Purpose |
|------------|----------|---------|
| `@theme_bg_color` | `#18181B` | Deep warm zinc/graphite window background |
| `@theme_base_color` | `#222226` | Card, sidebar, and container background |
| `@theme_surface_elevated` | `#2A2A2F` | Hovered rows, floating popovers, menus |
| `@theme_fg_color` | `#F4F4F5` | Primary text (Contrast ratio 12.8:1 against `#18181B`) |
| `@theme_text_secondary` | `#A1A1AA` | Secondary metadata text (Contrast ratio 5.6:1, exceeds WCAG AA) |
| `@theme_border_color` | `#3F3F46` | Subtle dividers and card outlines |
| `@accent_amber` | `#D97706` | Primary action accent, focus ring, key highlight |
| `@accent_amber_hover` | `#F59E0B` | Interactive hover state for accent elements |
| `@accent_terracotta` | `#C2410C` | Warning state, elevated package indicator |
| `@badge_user_green` | `#15803D` | User-scope badge (lime/emerald tint) |
| `@badge_system_graphite` | `#4B5563` | System-scope badge |
| `@destructive_rust` | `#DC2626` | Destructive actions, uninstall buttons, error states |

#### Light Theme
| Token Name | Hex Code | Purpose |
|------------|----------|---------|
| `@theme_bg_color` | `#FAF9F6` | Warm ivory/creamy light background |
| `@theme_base_color` | `#FFFFFF` | Card surface and list background |
| `@theme_surface_elevated` | `#F2F0EB` | Hovered rows, selection highlight |
| `@theme_fg_color` | `#18181B` | Primary text (Contrast ratio 14.1:1) |
| `@theme_text_secondary` | `#52525B` | Secondary metadata (Contrast ratio 6.2:1) |
| `@theme_border_color` | `#E4E4E7` | Container borders and separators |
| `@accent_amber` | `#B45309` | Adjusted dark amber for 4.5:1+ contrast on light surfaces |
| `@destructive_rust` | `#B91C1C` | High-contrast destructive red |

---

## 2. Typography

AppHarbor respects the desktop platform's system font settings while applying an intentional typographical hierarchy:
- **Title / App Name:** 18pt / Bold (`700`), letter-spacing: `-0.02em`
- **Section Headers:** 14pt / Semi-Bold (`600`)
- **Item Primary Name:** 13pt / Medium (`500`)
- **Body & Metadata:** 11pt / Regular (`400`)
- **Package Identifiers & Paths:** 10.5pt / Monospace (`Fira Code`, `JetBrains Mono`, `monospace`)
- **Source & Scope Chips:** 9.5pt / Semi-Bold (`600`), uppercase, tracking: `+0.04em`

---

## 3. Spacing, Sizing & Grid Rhythm

Following the 8dp / 4dp incremental spacing scale:
- **Padding - Micro:** 4px (between icon and badge text)
- **Padding - Compact:** 8px (inside chips, compact table cells)
- **Padding - Standard:** 12px (list row vertical padding, button padding)
- **Padding - Generous:** 16px (card interior, modal margins)
- **Corner Radii:**
  - Window & Dialogs: `12px`
  - Cards & Views: `8px`
  - Buttons & Inputs: `6px`
  - Filter & Source Chips: `9999px` (fully rounded pill)

---

## 4. Components & Interactive States

### 4.1 Filter Pills & Source Badges
Filter pills provide immediate feedback on active subsets:
- **All:** Counts all discoverable items.
- **Flatpak:** Rich blue-grey / amber badge indicating Flatpak provenance.
- **Snap:** Canary / snap badge.
- **AppImage:** Emerald / portable badge.
- **System:** Muted graphite pill.
- **User:** Soft forest green pill.
- **Unknown:** Dotted amber/terracotta border indicating caution and unknown origin.

### 4.2 Interactive States
- **Hover:** 150ms ease-out background shift to `@theme_surface_elevated`. No layout shifts or resizing.
- **Focus:** 2px solid `@accent_amber` outline with a 2px offset (`outline-offset: 2px`). Visible for all keyboard navigation (`Tab` and arrow keys).
- **Pressed/Active:** Slight scale or opacity reduction (`0.92`), immediate feedback.
- **Disabled:** 40% opacity, `pointer-events: none`, no cursor change.

### 4.3 Safe Uninstall Confirmation Dialog
A structured dialog that guarantees clarity:
1. **Header:** "Confirm Uninstallation" with application icon and name.
2. **Identification Section:** Display name, canonical package ID, detected source, scope, and physical installation path.
3. **Authorization Notice:** Indicates clearly if administrator privileges (Polkit) will be requested.
4. **Data Handling Checkbox:** Explicit opt-in checkbox ("Also remove application data and user settings"). Default is **UNCHECKED**. Shows specific directory targets (e.g., `~/.var/app/org.example.App`).
5. **Action Buttons:** "Cancel" (default focus, safe) and "Uninstall Application" (destructive red, requires deliberate click or shortcut).

---

## 5. Accessibility & Inclusivity

- **Contrast:** Strict compliance with WCAG 2.1 AA standards (minimum 4.5:1 for body and controls, 3:1 for large headers and icons).
- **Non-Color Indicators:** Every status, source, and scope has explicit text labels alongside distinct icon shapes. Color is never the sole communicator of state.
- **Screen Reader Support:** All widgets declare ATK/ATSPI accessible roles and descriptions.
- **Keyboard Navigation:** Full support for `Tab`, `Shift+Tab`, `Arrow Up/Down`, `Enter` to open details, and `Ctrl+F` to focus search.
