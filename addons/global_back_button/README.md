# Global Back Button — Odoo 19

**Quick Back Navigation in Backend Views**

## Overview

This module adds a universal **Back** button to every backend form/record view in Odoo 19. Instead of relying on breadcrumbs or the browser's native back button, users get a clearly-labeled, one-click control directly inside Odoo's control panel.

```
[ ← Back ]   Quotations / S00047
```

## Features

| Feature | Detail |
|---|---|
| One-click back | Returns to the previous list/kanban view instantly |
| All backend views | Works in Sales, Purchase, Inventory, Accounting, and every other app |
| Zero configuration | Install and it works — no settings needed |
| Native look & feel | Styled with Odoo's purple brand colors |
| Mobile friendly | Label hidden on small screens; icon-only mode |
| Accessible | Full keyboard navigation & reduced-motion support |
| Dark mode | Adapts to Odoo's dark theme |

## How It Works

The module patches Odoo's native `ControlPanel` Owl component using `@web/core/utils/patch`. It reads the current router state and shows the Back button whenever a form view (record) is open. Clicking the button calls `window.history.back()`, which triggers Odoo's own router to cleanly restore the previous view — no full page reload.

## Installation

1. Copy the `global_back_button` folder into your Odoo **addons** directory.
2. Restart the Odoo server.
3. Go to **Settings → Apps**, search for **Global Back Button**, and click **Install**.

## Compatibility

- Odoo **19.0** (Community & Enterprise)
- No external Python dependencies
- No database schema changes

## File Structure

```
global_back_button/
├── __init__.py
├── __manifest__.py
└── static/
    └── src/
        ├── js/
        │   └── global_back_button.js   ← ControlPanel patch
        ├── xml/
        │   └── global_back_button.xml  ← OWL template extension
        └── css/
            └── global_back_button.css  ← Styles
```

## License

LGPL-3
