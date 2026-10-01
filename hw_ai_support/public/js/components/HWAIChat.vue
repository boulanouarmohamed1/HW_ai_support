<template>
	<section class="hw-ai-chat" :dir="uiLanguage === 'ar' ? 'rtl' : 'ltr'" :class="{ 'hw-ai-rtl': uiLanguage === 'ar' }">
		<header class="hw-ai-header">
			<div><h3>{{ __("HW AI Support") }}</h3><p>{{ __("Ask about this ERPNext site") }}</p></div>
			<button class="btn btn-default btn-sm" @click="newConversation">{{ __("New conversation") }}</button>
		</header>
		<div ref="feed" class="hw-ai-feed" aria-live="polite">
			<div v-if="!messages.length" class="hw-ai-welcome">
				<p>{{ __("I can explain the documents, fields, workflows and Desk locations available to you.") }}</p>
				<div class="hw-ai-examples"><button v-for="example in examples" :key="example" class="btn btn-default btn-sm" @click="useExample(example)">{{ example }}</button></div>
			</div>
			<article v-for="(item, index) in messages" :key="index" class="hw-ai-message" :class="item.role" :dir="isArabic(item.content) ? 'rtl' : 'ltr'">
				<div class="hw-ai-bubble" v-html="safeFormat(item.content)"></div>
			</article>
			<div v-if="waiting" class="hw-ai-typing">{{ __("HW AI Support is typing…") }}</div>
		</div>
		<form class="hw-ai-composer" @submit.prevent="send">
			<label class="sr-only" for="hw-ai-message">{{ __("Your question") }}</label>
			<textarea id="hw-ai-message" v-model="message" :placeholder="__('Ask a question about ERPNext…')" :disabled="waiting" @keydown.enter.exact.prevent="send"></textarea>
			<button class="btn btn-primary" type="submit" :disabled="waiting || !message.trim()">{{ __("Send") }}</button>
		</form>
	</section>
</template>

<script>
import { nextTick } from "vue";

const examples = {
	en: ["What is a Sales Order?", "Where do I find customer invoices?", "Why is a delivery document used before invoicing?", "How do I create a quotation?"],
	fr: ["Qu’est-ce qu’une commande client ?", "Où trouver les factures client ?", "Pourquoi utiliser un document de livraison ?", "Comment créer un devis ?"],
	ar: ["ما هو أمر المبيعات؟", "أين أجد فواتير العملاء؟", "لماذا يُستخدم مستند التسليم قبل الفوترة؟", "كيف أنشئ عرض سعر؟"],
};

export default {
	data() {
		const lang = (frappe.boot?.lang || frappe.lang || "en").split("-")[0];
		return { uiLanguage: ["en", "fr", "ar"].includes(lang) ? lang : "en", message: "", messages: [], waiting: false };
	},
	computed: { examples() { return examples[this.uiLanguage]; } },
	methods: {
		__(text) { return __(text); },
		isArabic(text) { const chars = text.match(/[\u0600-\u06ff]/g)?.length || 0; return chars > Math.max(2, text.length * 0.2); },
		safeFormat(text) {
			let html = frappe.utils.escape_html(String(text));
			html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
			return html.replace(/\n/g, "<br>");
		},
		useExample(example) { this.message = example; this.send(); },
		newConversation() { this.messages = []; this.message = ""; },
		async scroll() { await nextTick(); this.$refs.feed.scrollTop = this.$refs.feed.scrollHeight; },
		async send() {
			const content = this.message.trim(); if (!content || this.waiting) return;
			this.messages.push({ role: "user", content }); this.message = ""; this.waiting = true; this.scroll();
			try {
				const response = await frappe.call({ method: "hw_ai_support.api.chat", type: "POST", args: { message: content, history: this.messages.slice(-10), language: this.uiLanguage } });
				this.messages.push({ role: "assistant", content: response.message.reply });
			} catch (error) {
				this.messages.push({ role: "assistant", content: __("I couldn’t process that question. Please try again.") });
			} finally { this.waiting = false; this.scroll(); }
		},
	},
};
</script>

<style scoped>
.hw-ai-chat { max-width: 920px; margin: 0 auto; border: 1px solid var(--border-color); border-radius: var(--border-radius-md); background: var(--fg-color); overflow: hidden; }
.hw-ai-header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 1.25rem; border-bottom:1px solid var(--border-color); }.hw-ai-header h3 { margin:0; font-size:1.1rem; }.hw-ai-header p { margin:.2rem 0 0; color:var(--text-muted); font-size:.875rem; }
.hw-ai-feed { height:min(58vh, 600px); overflow-y:auto; padding:1rem; background:var(--subtle-fg); }.hw-ai-welcome { color:var(--text-muted); padding:1rem 0; }.hw-ai-examples { display:flex; flex-wrap:wrap; gap:.5rem; }.hw-ai-examples button { white-space:normal; text-align:start; }
.hw-ai-message { display:flex; margin:.65rem 0; }.hw-ai-message.user { justify-content:flex-end; }.hw-ai-bubble { max-width:78%; padding:.7rem .9rem; border-radius:var(--border-radius-md); white-space:normal; overflow-wrap:anywhere; }.user .hw-ai-bubble { background:var(--primary); color:var(--primary-contrast); }.assistant .hw-ai-bubble { background:var(--fg-color); border:1px solid var(--border-color); color:var(--text-color); }.hw-ai-message[dir="rtl"] .hw-ai-bubble { text-align:right; }
.hw-ai-typing { color:var(--text-muted); font-size:.875rem; padding:.5rem; }.hw-ai-composer { display:flex; gap:.75rem; padding:1rem; border-top:1px solid var(--border-color); }.hw-ai-composer textarea { flex:1; min-height:46px; max-height:130px; resize:vertical; border:1px solid var(--border-color); border-radius:var(--border-radius); padding:.65rem; background:var(--control-bg); color:var(--text-color); }.hw-ai-rtl { text-align:right; }.hw-ai-rtl .hw-ai-composer { flex-direction:row-reverse; } @media (max-width: 576px) { .hw-ai-header { align-items:flex-start; flex-direction:column; }.hw-ai-feed { height:55vh; }.hw-ai-bubble { max-width:92%; }.hw-ai-composer { align-items:flex-end; } }
</style>
