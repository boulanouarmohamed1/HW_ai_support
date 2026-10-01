(function () {
	function add_button() {
		if (document.querySelector(".hw-ai-navbar-button")) return;
		const target = $(".navbar-nav.ml-auto, .navbar-right, header .navbar-nav").last();
		if (!target.length) return;
		const button = $("<button class='btn btn-default btn-sm hw-ai-navbar-button' type='button' aria-label='AI Assistant' title='AI Assistant'><svg class='icon icon-sm'><use href='#icon-message-circle'></use></svg></button>");
		button.on("click", () => frappe.set_route("hw-ai-chat"));
		target.prepend($("<li class='nav-item'></li>").append(button));
	}
	// Frappe v16 creates the Desk toolbar after app includes are evaluated.
	$(document).on("toolbar_setup", add_button);
	$(document).on("app_ready", () => setTimeout(add_button, 0));
	$(add_button);
})();
