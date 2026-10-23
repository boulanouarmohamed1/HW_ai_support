# User guide

Open **HW AI Support** from the ERPNext Desk, or visit `/app/hw-ai-chat` after signing in. Type a question or choose one of the sample questions. Start a new conversation to clear the visible chat. The assistant is read-only: use ERPNext forms and reports to make business changes.

Answers depend on the language provider being configured. Live business answers additionally depend on the administrator enabling the Phase 2 tools and the signed-in user's ERPNext permissions. If a question asks for data outside the available tools, the assistant should say it cannot retrieve that data rather than guess.

## English

Examples:

- “What is a Sales Order?”
- “How do I create a quotation?”
- “Where do I find a Purchase Invoice?”
- “What is the stock for item SKU_001?”
- “Which supplier invoices are overdue?”
- “What were sales from 2026-01-01 to 2026-01-31?”
- “What was the net profit from 2026-01-01 to 2026-01-31?”

For sales or profit questions, use dates that fall within the site's accounting data and the company selected as your ERPNext default. Stock and invoice totals reflect the data visible to your account.

## Français

Exemples :

- « Qu’est-ce qu’une commande client ? »
- « Comment créer un devis ? »
- « Où trouver une facture d’achat ? »
- « Quel est le stock de l’article SKU_001 ? »
- « Quelles factures fournisseur sont en retard ? »
- « Quel était le total des ventes du 01/01/2026 au 31/01/2026 ? »
- « Quel était le bénéfice net du 01/01/2026 au 31/01/2026 ? »

Les résultats dépendent des données et des autorisations de votre compte ERPNext.

## العربية

أمثلة:

- «ما هو أمر المبيعات؟»
- «كيف أنشئ عرض سعر؟»
- «أين أجد فاتورة شراء؟»
- «ما كمية مخزون الصنف SKU_001؟»
- «ما فواتير الموردين المتأخرة؟»
- «ما إجمالي المبيعات من 2026-01-01 إلى 2026-01-31؟»
- «ما صافي الربح من 2026-01-01 إلى 2026-01-31؟»

تظهر رسائل العربية باتجاه من اليمين إلى اليسار. تعتمد النتائج على بيانات ERPNext والصلاحيات المتاحة لحسابك.

## Questions the current release cannot answer

The app does not currently retrieve employee leave balances, payroll values, arbitrary reports, or perform actions such as creating quotations or submitting invoices. It also does not answer unrelated general-knowledge questions. See [supported tools and boundaries](tools_and_scope.md).
