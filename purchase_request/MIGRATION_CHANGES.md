# Purchase Request - Odoo 17 to Odoo 18 Community Migration Changes

## Version Update

- `__manifest__.py`: Version changed from `17.0.1.2.3` to `18.0.1.0.0`

## XML View Changes (tree -> list)

Odoo 18 renamed the `tree` view type to `list`. All occurrences were updated across the module.

### Tag Replacements

| File | Change |
|------|--------|
| `views/purchase_request_view.xml` | `<tree>` / `</tree>` tags replaced with `<list>` / `</list>` (3 occurrences: main form line_ids inline list, BoM references inline list, main tree/list view) |
| `views/purchase_request_line_view.xml` | `<tree>` / `</tree>` tags replaced with `<list>` / `</list>` (3 occurrences: main list view, allocations inline list, purchase order lines sub-list) |
| `views/stock_move_views.xml` | `<tree>` / `</tree>` replaced with `<list>` / `</list>` (allocations list view) |
| `wizard/purchase_request_line_make_purchase_order_view.xml` | `<tree>` / `</tree>` replaced with `<list>` / `</list>` (wizard item_ids inline list) |

### XPath Expression Updates

| File | Old XPath | New XPath |
|------|-----------|-----------|
| `views/purchase_order_view.xml` | `//field[@name='order_line']/tree` | `//field[@name='order_line']/list` |
| `views/purchase_order_view.xml` | `//tree` | `//list` |
| `views/purchase_request_view.xml` | `//field[@name='order_line']/tree/field[...]` | `//field[@name='order_line']/list/field[...]` (2 active + 1 commented) |

### view_mode Field Updates

| File | Old Value | New Value |
|------|-----------|-----------|
| `views/purchase_request_view.xml` | `tree,form` | `list,form` |
| `views/purchase_request_line_view.xml` | `tree,form` | `list,form` |
| `views/purchase_request_line_view.xml` | `<field name="view_mode">tree</field>` (act_window.view record) | `<field name="view_mode">list</field>` |

### Other Attribute Updates

| File | Old Value | New Value |
|------|-----------|-----------|
| `views/purchase_request_line_view.xml` | `mode="tree"` | `mode="list"` |
| `views/purchase_request_line_view.xml` | `'tree_view_ref'` (context key) | `'list_view_ref'` |

## Removed XPath References (Fields/Buttons not in Odoo 18 Community)

| File | Removed XPath | Reason |
|------|---------------|--------|
| `views/purchase_request_view.xml` | `//field[@name='amount_to_invoice']` | Field does not exist in Odoo 18 Community `sale.order` list view |
| `views/purchase_request_view.xml` | `//button[@name='action_create_pr']` | Button defined in `so_to_pr.xml` which loads after this file; xpath would fail |

## Python Model Changes

No Python changes were required. The models already use Odoo 18 compatible patterns:
- `@api.model_create_multi` (correct for v18)
- Modern `@api.depends` / `@api.onchange` decorators
- No deprecated `attrs=` or `states=` XML attributes
- No deprecated Python API calls

## Security / Data / Reports

No changes required - all compatible with Odoo 18.

## Summary

All changes are related to the Odoo 18 `tree` -> `list` view type rename. No Python model code, security rules, data files, or report templates required modification.