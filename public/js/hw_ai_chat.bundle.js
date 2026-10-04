import { createApp, nextTick } from "vue";
import HWAIChat from "./components/HWAIChat.vue";

frappe.provide("hw_ai_support");
hw_ai_support.mount_chat = (element) => {
	if (element.__hw_ai_app__) element.__hw_ai_app__.unmount();
	element.innerHTML = "";
	element.__hw_ai_app__ = createApp(HWAIChat).mount(element);
};
