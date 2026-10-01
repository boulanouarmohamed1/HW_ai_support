(function () {
	function add_button() {
		if (document.querySelector(".hw-ai-navbar-button") || !frappe?.ui?.toolbar) return;
		const button = $("<button class='btn btn-default btn-sm hw-ai-navbar-button' type='button' aria-label='AI Assistant' title='AI Assistant'><svg class='icon icon-sm'><use href='#icon-message-circle'></use></svg></button>");
		button.on("click", () => frappe.set_route("hw-ai-chat"));
		const target = $(".navbar .navbar-nav").last();
		if (target.length) target.prepend($("<li class='nav-item'></li>").append(button));
	}
	$(document).on("app_ready", add_button);
	setTimeout(add_button, 1200);
})();
