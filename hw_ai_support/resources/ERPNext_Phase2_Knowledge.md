---
title: ERPNext and Frappe HR operational guide for HW AI Support
kind: curated_reference
language: en
product_scope: ERPNext and Frappe HR
version_note: Current official documentation consulted 2026-10-23; navigation and features may vary by installed version and local configuration.
---

# ERPNext and Frappe HR operational guide

This guide is a retrieval source for HW AI Support. Use it to answer questions about leave applications and approvals, stock reports, and the Profit and Loss Statement. Explain the documented steps and distinguish them from live ERP data.

## How to route a question

- A question asking **how to perform a process** is a documentation question. Answer from the relevant procedure below and mention when menu labels may differ by version.
- A question asking for **a current number or named record** (for example, an employee's remaining leave, current item quantity, or overdue invoices) requires an enabled, permission-checked live-data tool. Documentation is not evidence of a site's current values.
- Do not answer an employee-specific leave balance, stock quantity, invoice amount, or financial figure by guessing. If the live tool is unavailable or access is denied, say that the current site data could not be retrieved.
- The user's role and the site's configured workflows determine what they can see and do. Never promise that a user can approve or access a record merely because the standard feature exists.

## Employee leave requests and manager approval

Frappe HR uses a **Leave Application** for an employee's request. A standard process normally needs an Employee, Department, Leave Period, Holiday List, Leave Type, Leave Policy, and submitted Leave Allocation. Administrators should verify that the correct leave types and allocations exist before employees submit requests.

### Employee submits a leave request

Official source: [Frappe HR Leave Application](https://docs.frappe.io/hr/leave-application)

1. Open **Human Resources > Leaves > Leave Application** (the workspace label can vary by version and workspace configuration).
2. Create a new Leave Application and select the employee and leave type.
3. Enter the start and end dates. Review the calculated leave days and balance shown by the form. Mark a half day when appropriate and enter the reason if required by company policy.
4. Select the Leave Approver. Check **Follow via Email** if the approver should receive email notification.
5. Save the request. It enters the open/pending approval state; the approver reviews and approves, rejects, or cancels it according to their permissions. The employee can be notified of the outcome.

The employee must have permission to create their own Leave Application. Administrators can configure user permissions and employee matching so employees see only their own records. Exact permission setup is site-specific and should be checked with a System Manager.

### Assign the manager or leave approver

Official source: [Frappe HR Leave Application](https://docs.frappe.io/hr/leave-application)

The approver can be assigned at the **Employee** level in the employee record's **Attendance and Leave Details** section. An approver can also be set for a **Department**. A department approver can apply to employees in that department; an employee-specific approver is the employee's default where both are set. Confirm the intended default in a test Leave Application before rollout.

The approver must have the permissions required to review and submit the Leave Application. If the approver does not have access, an administrator should correct roles or permissions rather than relying on an AI response to bypass access controls.

### Is a general Workflow required?

Official sources: [ERPNext Workflows](https://docs.frappe.io/erpnext/workflows), [Workflow Actions](https://docs.frappe.io/erpnext/workflow-actions)

For a basic leave approval, use Frappe HR's Leave Approver fields and Leave Application process. A separate ERPNext **Workflow** is only needed when the organization requires additional or multi-level approval states beyond the standard leave approver flow.

To configure an additional workflow, open **Settings > Workflow**, select the target document type, define the states and transitions, and restrict each transition to the appropriate role. Configure workflow email alerts if approvers should receive email. Use **Workflow Actions** to review pending actions. Test the workflow with employee, manager, and HR roles before enabling it for everyone. Do not create a second approval flow until you have checked how it interacts with the standard Leave Application approver.

### Check remaining leave days

Official sources: [Employee Leave Balance Summary](https://docs.frappe.io/hr/reports/employee-leave-balance-summary), [Leave Ledger Report](https://docs.frappe.io/hr/leave-ledger-report)

Use **Employee Leave Balance Summary** to see an employee's balance by leave type. Select the date and company; optionally filter by employee, department, or employee status. A submitted Leave Allocation must cover the selected date. The report uses the active allocation and accounts for allocated, carried-forward, adjusted, taken, and expired leave. Approved future leave within the same allocation can also reduce the reported balance. If there is no allocation for a leave type on the selected date, the report shows zero for it.

For the ledger history behind a balance, use **Leave Ledger Report**. It shows leave allocations, applications, encashments, and leave ledger movements. Access to these reports is restricted by roles and employee permissions.

**Answer boundary:** the steps above explain where to check the balance. To tell a user the actual remaining days for a named employee, the assistant must call a live HR data tool that checks that user's permissions. If that tool is not implemented or enabled, explain how to open the report instead of inventing a balance.

## Stock quantity and stock movement

### Current stock quantity

Official sources: [Quick Stock Balance](https://docs.frappe.io/erpnext/quick-stock-balance), [Stock Level Report](https://docs.frappe.io/erpnext/stock-level-report)

Use **Stock > Tools > Quick Stock Balance** to check an item's quantity and value for a selected warehouse and date. The item and warehouse identify the scope of the result. The tool can open the Stock Balance Report with those filters applied.

The **Stock Balance Report** reports inventory quantity and value for its selected filters and date range. Clarify whether the user means actual quantity on hand in one warehouse or projected quantity across supply and demand.

The **Stock Projected Quantity Report** can show actual, planned, requested, ordered, and reserved quantities. Projected quantity is calculated as:

`Actual Qty + Planned Qty + Requested Qty + Ordered Qty - Reserved Qty`

This projected figure is not the same as physical stock currently available in a warehouse.

### Stock movement history

Official source: [Stock Ledger Report](https://docs.frappe.io/erpnext/stock-ledger)

Use the **Stock Ledger Report** to inspect inventory movements over time. It shows item and warehouse details, quantities, valuation, and the transactions that produced the movements. Relevant source transactions include Purchase Receipts, Delivery Notes, Stock Entries, Stock Reconciliations, and Sales or Purchase Invoices when **Update Stock** applies.

**Answer boundary:** actual quantity and valuation are live site data. A document explaining the report cannot provide the current balance. Ask for or resolve the item and warehouse, then use an authorized live stock tool; otherwise direct the user to Quick Stock Balance or the Stock Balance Report.

## Profit and Loss Statement

Official sources: [Profit and Loss Report](https://docs.frappe.io/erpnext/profit-and-loss-report), [Accounting Reports](https://docs.frappe.io/erpnext/accounting-reports)

The **Profit and Loss Statement** summarizes income and expenses over a selected period. It reports accounting performance; it is not a bank balance or cash-flow report. A profitable period does not mean the same amount is available as cash.

To review it:

1. Open **Accounting > Profit and Loss Statement** (workspace labels can vary).
2. Select the Company and fiscal year or date range.
3. Review periodicity, Finance Book, cost center, project, department, currency, and other dimensions. These filters change which entries are included or how values are displayed.
4. Expand income and expense groups to inspect accounts. Drill into a value to review the underlying ledger entries.
5. If the report is empty, confirm submitted transactions exist in the selected period and company, then review filters and account root types.

When comparing the statement with the General Ledger, use matching company, dates, Finance Book, dimensions, currency, and period-closing options. If the monthly columns look cumulative, review **Accumulated Values** and the report's periodicity.

**Answer boundary:** a request such as “Show this year's Profit and Loss” needs an enabled live report tool, company context, fiscal-year dates, and permission to read the report. If those are unavailable, give the navigation steps above and state that you cannot fetch the site's figures.

## Site-specific information to add before production

This guide describes standard documentation, not this site's custom configuration. A System Manager should fill in and maintain these facts for the deployed site:

- ERPNext version and Frappe HR app version: **verify on the site**.
- Company names and default fiscal year: **site-specific; do not infer**.
- Exact workspace/menu labels and report names: **verify on the site's Workspaces**.
- Whether employee self-service Leave Applications are enabled: **verify role and User Permission rules**.
- Whether approvers are assigned per Employee, per Department, or both: **verify employee and department records**.
- Whether a custom Leave Application Workflow overrides or extends the standard approval route: **inspect active Workflow records**.
- Which live-data tools are enabled in HW AI Support Settings: **verify application settings**.

Do not fill these items with assumptions. Answers about company configuration must come from the current site, an administrator-approved configuration guide, or a permission-checked live tool.

## Official source references

- Frappe HR, [Leaves overview](https://docs.frappe.io/hr/leaves)
- Frappe HR, [Leave Application](https://docs.frappe.io/hr/leave-application)
- Frappe HR, [Employee Leave Balance Summary](https://docs.frappe.io/hr/reports/employee-leave-balance-summary)
- Frappe HR, [Leave Ledger Report](https://docs.frappe.io/hr/leave-ledger-report)
- ERPNext, [Workflows](https://docs.frappe.io/erpnext/workflows)
- ERPNext, [Workflow Actions](https://docs.frappe.io/erpnext/workflow-actions)
- ERPNext, [Quick Stock Balance](https://docs.frappe.io/erpnext/quick-stock-balance)
- ERPNext, [Stock Level Report](https://docs.frappe.io/erpnext/stock-level-report)
- ERPNext, [Stock Ledger Report](https://docs.frappe.io/erpnext/stock-ledger)
- ERPNext, [Profit and Loss Report](https://docs.frappe.io/erpnext/profit-and-loss-report)
- ERPNext, [Accounting Reports](https://docs.frappe.io/erpnext/accounting-reports)
