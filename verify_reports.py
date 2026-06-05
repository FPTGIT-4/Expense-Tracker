import os
os.chdir(r"f:\EXPENCE TRACKER 1 JUNE 2026")

checks = []

tmpl = open(r"reports\templates\reports\dashboard.html", encoding="utf-8").read()
checks.append(("No broken multi-line tag",     "floatformat:1\n" not in tmpl and "floatformat:1\r\n" not in tmpl))
checks.append(("No dollar signs",              "${{" not in tmpl and ">$" not in tmpl))
checks.append(("Has rupee symbol",             "&#8377;" in tmpl or "\u20b9" in tmpl))
checks.append(("Has percentage display",       "floatformat:1 }}%" in tmpl))
checks.append(("Has category_report loop",     "for item in category_report" in tmpl))
checks.append(("Has source_report loop",       "for item in source_report" in tmpl))
checks.append(("Has transactions loop",        "for tx in recent_transactions" in tmpl))
checks.append(("Has monthly_summary loop",     "for month in monthly_summary" in tmpl))
checks.append(("Has date filter buttons",      "date_filter=today" in tmpl and "date_filter=this_year" in tmpl))
checks.append(("Has custom date range form",   "date_filter=custom" in tmpl))

base = open(r"templates\base.html", encoding="utf-8").read()
checks.append(("Navbar has Reports link",      "reports-dashboard" in base))

views = open(r"reports\views.py", encoding="utf-8").read()
checks.append(("View handles today filter",    "'today'" in views))
checks.append(("View handles this_week",       "'this_week'" in views))
checks.append(("View handles this_month",      "'this_month'" in views))
checks.append(("View handles this_year",       "'this_year'" in views))
checks.append(("View handles custom range",    "'custom'" in views))
checks.append(("View has LoginRequiredMixin",  "LoginRequiredMixin" in views))

svc = open(r"reports\services.py", encoding="utf-8").read()
checks.append(("Service calculates income",    "total_income" in svc))
checks.append(("Service calculates expenses",  "total_expenses" in svc))
checks.append(("Service calculates balance",   "current_balance" in svc))
checks.append(("Service builds category_report","category_report" in svc))
checks.append(("Service builds source_report", "source_report" in svc))
checks.append(("Service user-filters data",    "user=user" in svc))

print("=" * 55)
print("  REPORTS MODULE - FULL VERIFICATION")
print("=" * 55)
all_pass = True
for label, result in checks:
    status = "PASS" if result else "FAIL"
    if not result:
        all_pass = False
    print(f"  [{status}] {label}")
print("=" * 55)
print("  RESULT:", "ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED")
print("=" * 55)
