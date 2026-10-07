#!/usr/bin/env python3
"""
Star Travels ERP — Local CI Pre-Flight Verification Runner
Runs all linting, schema validation, XML structure checks, and E2E tests locally
before pushing commits to ensure a guaranteed pass on GitHub Actions CI.
"""
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")


def run_step(step_name, command):
    print("\n========================================================")
    print(f"-> STEP: {step_name}")
    print(f"   Command: {command}")
    print("========================================================")
    ret = subprocess.call(command, shell=True)
    if ret != 0:
        print(f"FAILED: Step '{step_name}' exited with error code {ret}!")
        sys.exit(ret)
    print(f"PASSED: Step '{step_name}' succeeded.")


def main():
    print("Starting Star Travels ERP Local CI Pre-Flight Checks...")

    # 1. Ruff Linter
    run_step("1. Python Linting (Ruff)", "python -m ruff check .")

    # 2. XML View & Manifest Validation
    run_step(
        "2. XML Views & Manifests Structure Validation",
        """python -c "
import os, sys, xml.etree.ElementTree as ET
failed = False
count = 0
for root, _, files in os.walk('odoo_addons'):
    for f in files:
        if f.endswith('.xml'):
            p = os.path.join(root, f)
            try:
                ET.parse(p)
                count += 1
            except Exception as e:
                print(f'XML Error in {p}: {e}', file=sys.stderr)
                failed = True
if failed:
    sys.exit(1)
print(f'Successfully parsed and validated {count} XML view/data templates!')
" """,
    )

    # 3. JSON Contract Validation
    run_step(
        "3. JSON Contract Schemas Validation",
        """python -c "
import os, sys, json
count = 0
for root, _, files in os.walk('contracts'):
    for f in files:
        if f.endswith('.json'):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fh:
                json.load(fh)
                count += 1
print(f'Successfully validated {count} JSON contract schemas!')
" """,
    )

    # 4. Pytest Live E2E Integration Suite
    run_step("4. Pytest Live E2E Integration Suite", "python -m pytest tests/ -v")

    print("\n********************************************************")
    print("ALL LOCAL PRE-FLIGHT CI CHECKS PASSED SUCCESSFULLY (100% GREEN)!")
    print("Your code is completely clean and ready to commit & push.")
    print("********************************************************")


if __name__ == "__main__":
    main()
