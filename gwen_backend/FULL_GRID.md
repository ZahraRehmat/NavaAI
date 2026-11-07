# Manual full grid

This is an optional manual mouse mode. Qwen and the existing Office/browser/app/file routes remain unchanged outside it. Type commands in the corner chat or use the [offline voice module](OFFLINE_VOICE.md), starting with **Gwen full grid**.

## Commands

| Type | Result |
|---|---|
| `Gwen full grid` | Enable a click-through 40-column × 25-row grid over connected displays |
| `C3` | Move to C3's center and single-click |
| `move to C3` | Move to C3's center without clicking |
| `click C3` / `double click C3` / `right click C3` | Move there and perform the specified click |
| `scroll down on G4` / `scroll up 3 on G4` | Move to that area and send wheel input there |
| `scroll left on G4` / `scroll right on G4` | Horizontal wheel input where supported |
| `hold C3` / `hold right C3` | Hold a mouse button at the point |
| `D3` while holding | Move the held pointer to D3 |
| `release` / `drop` | Release held mouse buttons |
| `move left 1` / `move right 40` / `move up` / `move down` | Pixel movement; default 40 pixels |
| `drag C3 to E3` | Smooth left-button drag, then release |
| `hold C3 and move right 100 and release` | One continuous gesture; useful while testing through a typed chat |
| `zoom C3` | Subdivide that cell for finer targeting |
| `zoom out` / `reset grid` | Back up one subdivision / restore full coverage |
| `pixel 1919 1199` | Exact physical pixel, if it belongs to a connected display |
| `grid size 20 by 12` | Change current grid density |
| `exit grid` / `grid off` | Remove overlays, release buttons and restore agent routing |
| **F8** | Emergency stop: release buttons and exit grid |

Commands can be chained with semicolons or `then`. The whole chain is parsed before input, so an invalid phrase does not accidentally execute an earlier click. A failed later operation releases held buttons; completed earlier steps remain completed.

## Mapping and precision

Every display rectangle is partitioned with integer, half-open bounds, including its final row/column of pixels. No pixels on a physical display are left out. A label addresses a cell center, not every pixel inside it individually. Zooming and one-pixel movement/exact-pixel commands provide finer access. The denser default has 1,000 cells, approximately 48×48 pixels on a 1920×1200 screen, compared with the original 120×120 cells. Labels on the primary monitor are A1–AN25; secondary displays use M2-A1, M3-A1, etc. Mirrored monitor rectangles share one grid. Virtual gaps between monitors have no physical pixels and cannot be clicked.

Full-grid labels are tied to screen positions, not detected buttons, and stay stable when app content changes. Moving to a label on a new page still means that same screen position. If a display is unplugged/rearranged, the pending command is cancelled and the grid is rebuilt. Zoom is bounded to keep its labels legible; use pixel nudges for the final few pixels.

The most recent grid point is remembered independently of physical mouse movement back to the typed chat. A subsequent plain `click`, `hold` or `scroll down` returns to that grid point first. In typed testing, use a single `drag ... to ...` or a hold/move/release chain for continuous application gestures: activating another window between separate commands can cancel some apps' drag capture. Voice integration can avoid that focus change later.

## Safety and limits

Overlays are transparent to mouse input and do not take keyboard focus. Clicking/scrolling still respects Windows process-integrity restrictions; the grid never elevates Gwen. F8/exit/error/quit release buttons held by Gwen. Unlike the AI mouse backend, moving to a real screen corner is permitted in this explicit manual mode; F8 is the emergency release.

While the grid is active, commands go only to the grid parser; exit it to delegate an agent task. `Gwen grid` switches to the adaptive target-based [smart grid](SMART_GRID.md). Application-specific drag, scroll and protected-desktop behavior can vary.

## Verification

Unit checks exhaustively cover every pixel of simulated odd-size/negative-coordinate monitor layouts exactly once, and test screen corners, movement, zoom, stopping, invalid instructions, topology changes and retained pointer position. `diagnostics/full-grid-ui-verification.json` records a real typed-chat test: label-only movement, double-click, right-click, targeted scroll, hold/move/release, dragging and F8 release on an isolated test surface. Actual live testing used one 1920×1200 display; additional monitors are covered by geometry tests, not a live multi-monitor test.
