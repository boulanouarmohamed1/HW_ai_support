frappe.pages["hw-ai-chat"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("HW AI Support"),
		single_column: true,
	});
	frappe.require("hw_ai_chat.bundle.js").then(() => {
		hw_ai_support.mount_chat(page.main.get(0));
	});
};
