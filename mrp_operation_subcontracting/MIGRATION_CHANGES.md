# MRP Operation Subcontracting - Odoo 17 to Odoo 18 Community Migration Changes

## Manifest Changes

- `__manifest__.py`: Reordered data files — moved `wizard/swapping_customer.xml` before `views/sale_bom_view.xml` (the view references an action defined in the wizard file)

## XML View Changes

### 1. tree -> list Rename (Odoo 18 breaking change)

Odoo 18 renamed the `tree` view type to `list`. All occurrences were updated.

#### Tag Replacements (`<tree>` -> `<list>`)

| File | Details |
|------|---------|
| `views/sale_order_status.xml` | `<tree>`/`</tree>` replaced with `<list>`/`</list>` (sale order status list view) |
| `views/sale_order_status.xml` | `view_mode` changed from `kanban,tree` to `kanban,list` |

#### view_mode Updates (`tree,form` -> `list,form`)

| File | Details |
|------|---------|
| `views/mrp_production_views.xml` | 2 action records updated |
| `views/similar_work_order_view.xml` | 1 action record updated |

#### XPath Expression Updates

| File | Old | New |
|------|-----|-----|
| `views/custom_view.xml` | `//field[@name='order_line']/tree/field[@name='name']` | `//field[@name='order_line']/list/field[@name='name']` |

#### Context Key Updates

| File | Old | New |
|------|-----|-----|
| `views/mrp_production_views.xml` | `'tree_view_ref'` | `'list_view_ref'` |

### 2. XPath Targets Fixed (Enterprise -> Community)

Elements that exist in Odoo 17 Enterprise but not in Odoo 18 Community.

| File | Old XPath | Fix |
|------|-----------|-----|
| `views/sale_bom_view.xml` | `//header/button[@name='action_open_label_type']` | Changed to `//header/button[@name='button_unbuild']` (button doesn't exist in Community) |

### 3. Missing XML ID Fix

| File | Issue | Fix |
|------|-------|-----|
| `views/sale_bom_view.xml` | Referenced `action_swapping_order_new` before it was defined | Fixed by reordering `__manifest__.py` data files |

## Python Changes

### `models/sale_bom.py` — tree -> list in action dictionaries

All Python action return dictionaries updated:

| Method | Change |
|--------|--------|
| `action_yet_to_start_orders()` | `'view_mode': 'tree,form'` -> `'list,form'`, `'views': [(id, 'tree')]` -> `[(id, 'list')]` |
| `action_processing_orders()` | Same changes |
| `action_partially_ready_orders()` | Same changes |
| `action_ready_orders()` | Same changes |
| `action_invoiced_orders()` | Same changes |
| `action_view_done_mrp_orders()` | `'view_mode': 'tree,form'` -> `'list,form'` |

## Files NOT Changed (Already Compatible)

- `models/mrp_production.py` — Already uses v18 API patterns
- `models/mrp_workcenter.py` — No deprecated patterns
- `models/mrp_workorder.py` — No deprecated patterns
- `models/mrp_checklist.py` — Already uses `<list>` tags
- `models/scrap.py` — No deprecated patterns
- `models/similar_work_order.py` — No deprecated patterns
- `wizard/customer_swap.py` — No deprecated patterns
- `security/ir.model.access.csv` — Compatible
- `data/*.xml` — Compatible
- `views/mrp_workcenter_views.xml` — Compatible
- `views/stock_scrap.xml` — Compatible
- `views/templates.xml` — Compatible
- `wizard/swapping_customer.xml` — Compatible

## Backup/Duplicate Files (Not loaded, no changes needed)

These files are NOT referenced in `__manifest__.py` or `__init__.py`:
- `__manifest__1.py`
- `models/sale_bom1.py`
- `views/mrp_production_views1.xml`
- `views/mrp_production_views2.xml`
- `views/sale_order_status1.xml`
- `security/ir.model.access1.csv`

## Summary

Main changes:
1. All `tree` -> `list` renames (XML tags, view_mode, xpaths, context keys, Python dicts)
2. Fixed xpath targeting Enterprise-only button (`action_open_label_type`)
3. Fixed manifest data file ordering for XML ID dependency