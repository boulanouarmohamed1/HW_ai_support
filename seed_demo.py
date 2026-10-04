from __future__ import annotations
import frappe

def run():
	company = frappe.db.get_single_value('Global Defaults', 'default_company') or frappe.db.get_value('Company', {}, 'name')
	if not company:
		frappe.throw('Create a company first')
	warehouse = frappe.db.get_value('Warehouse', {'warehouse_name': 'HW Demo Warehouse'})
	if not warehouse:
		warehouse = frappe.get_doc({'doctype':'Warehouse','warehouse_name':'HW Demo Warehouse','company':company,'is_group':0}).insert(ignore_permissions=True).name
	item = frappe.db.get_value('Item', {'item_code':'SKU_001'})
	if not item:
		item = frappe.get_doc({'doctype':'Item','item_code':'SKU_001','item_name':'Demo Support Item','item_group':frappe.db.get_value('Item Group', {}, 'name'),'stock_uom':'Nos','is_stock_item':1}).insert(ignore_permissions=True).name
	bin_name = frappe.db.get_value('Bin', {'item_code':item,'warehouse':warehouse})
	if not bin_name:
		b=frappe.get_doc({'doctype':'Bin','item_code':item,'warehouse':warehouse}).insert(ignore_permissions=True)
	else:
		b=frappe.get_doc('Bin',bin_name)
	b.db_set('actual_qty',42,update_modified=False)
	b.db_set('projected_qty',42,update_modified=False)
	settings=frappe.get_single('HW AI Support Settings')
	settings.tools_enabled=1
	settings.business_data_mode='Local LLM only'
	settings.pseudonymize_parties=1
	settings.save(ignore_permissions=True)
	frappe.db.commit()
	return {'company':company,'warehouse':warehouse,'item':item,'quantity':42,'tools_enabled':1}
import frappe

def fix_module():
	frappe.db.set_value('DocType', 'HW AI Support Settings', 'module', 'Hw Ai Support', update_modified=False)
	frappe.db.commit()
	return 'fixed'
def show_module():
	import frappe
	print(frappe.db.get_value('DocType','HW AI Support Settings','module'))
def set_demo_quantity(quantity=100):
	import frappe
	warehouse = frappe.db.get_value('Warehouse', {'warehouse_name': 'HW Demo Warehouse'})
	bin_name = frappe.db.get_value('Bin', {'item_code': 'SKU_001', 'warehouse': warehouse})
	if not bin_name:
		frappe.throw('Demo Bin was not found. Run seed_demo.run first.')
	b = frappe.get_doc('Bin', bin_name)
	b.db_set('actual_qty', float(quantity), update_modified=False)
	b.db_set('projected_qty', float(quantity), update_modified=False)
	frappe.db.commit()
	return {'item': 'SKU_001', 'warehouse': warehouse, 'quantity': float(quantity)}
