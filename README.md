# Cashly — Personal Finance & Budgeting Application

Cashly is a modern, full-featured personal finance application built with **Django** and powered by **PyBasics Kit** (`pybasics_kit`) for reusable financial and mathematical calculations.

---

## 🎨 Design & UI
- **Typography:** [Outfit](https://fonts.google.com/specimen/Outfit) from Google Fonts.
- **Color Theme:** **Light Green** (Emerald, Mint, and Sage tones `#10b981`, `#059669`, `#ecfdf5`, `#d1fae5`, `#0f172a`) with card surfaces and subtle glassmorphic touches.
- **Charts:** Chart.js powered 6-month cash flow trends & donut category distribution.
- **Responsive:** Desktop sidebar navigation, mobile drawer toggle, and quick global transaction modal.

---

## 🏗️ Architecture & PyBasics Kit Integration

```
Cashly (Django Application)
  ├── Models: Category, Transaction, Budget, SavingsGoal, NotificationReminder
  ├── Groups & Permissions: Standard User, Financial Manager, Auditor, Viewer
  └── Services:
        ├── finances/services/calculator.py ──> Calls pybasics_kit functions
        └── finances/services/alerts.py     ──> Automated threshold alerts
```

Cashly separates user interaction and database persistence from core math:
- `pybasics_kit.calculate_balance(income, expenses)`
- `pybasics_kit.calculate_total_expenses(expenses)`
- `pybasics_kit.calculate_savings(income, expenses)`
- `pybasics_kit.calculate_savings_rate(income, savings)`
- `pybasics_kit.calculate_budget_remaining(budget, spending)`
- `pybasics_kit.calculate_budget_usage(spending, budget)`
- `pybasics_kit.calculate_daily_budget(remaining, days)`
- `pybasics_kit.calculate_percentage(value, total)`
- `pybasics_kit.calculate_percentage_change(old, new)`

---

## 🔐 Users, Groups, and Permissions

Cashly provides a multi-role security and permission system backed by Django's `auth.models.Group` and `auth.models.Permission`:

1. **Standard User (Default):**
   - Record, view, edit, and delete personal transactions, budgets, and savings goals.
   - User data is strictly isolated so users can only view their own records.
2. **Financial Manager:**
   - Standard capabilities plus permissions to manage shared global categories, export transactions (`can_export_transactions`), override budget limits, and audit records.
3. **Auditor:**
   - Read-only across budgets, transactions, and analytics with system auditing permission (`can_audit_all_transactions`) and CSV export.
4. **Viewer:**
   - Read-only access for family members or viewers.

---

## 🚀 Quick Start

### 1. Run Migrations & Seed Data
```bash
python manage.py migrate
python manage.py seed_cashly
```

### 2. Run the Development Server
```bash
python manage.py runserver
```
Visit: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 3. Pre-Seeded Demo Logins
- **Standard User (Alex Mugisha):**
  - Username: `demo`
  - Password: `demo12345`
  - Preloaded with salary, freelance income, diverse expenses, active budgets, and savings goals.
- **Financial Manager:**
  - Username: `manager`
  - Password: `manager12345`
  - Has system-wide auditing and report export clearance.

*(Note: Both accounts can also be accessed with 1-click on the Sign-In screen!)*

---

## 🧪 Automated Tests
Run the test suite:
```bash
python manage.py test
```
