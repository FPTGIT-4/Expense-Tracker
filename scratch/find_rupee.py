import os

path = r"f:\EXPENCE TRACKER 1 JUNE 2026\dashboard\templates\dashboard\dashboard.html"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "₹" in line or "&#8377;" in line:
        safe_line = line.strip().replace("₹", "RUPEE").replace("&#8377;", "RUPEE")
        print(f"Line {idx+1}: {safe_line}")
