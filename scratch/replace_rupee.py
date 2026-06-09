import os

path = r"f:\EXPENCE TRACKER 1 JUNE 2026\dashboard\templates\dashboard\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace any occurrence of the raw Rupee sign with {{ currency_symbol }}
# We must be careful not to replace it if it's already part of {{ currency_symbol }}.
# However, in dashboard.html, let's just do standard replacements.
# Let's replace '₹' with '{{ currency_symbol }}'
# And also '&#8377;' with '{{ currency_symbol }}'

content = content.replace("&#8377;", "{{ currency_symbol }}")
content = content.replace("₹", "{{ currency_symbol }}")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("SUCCESS: Replaced currency symbols.")
