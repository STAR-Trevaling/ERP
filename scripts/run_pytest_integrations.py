import os
import sys

os.environ["DJANGO_DEBUG"] = "1"
os.environ["DJANGO_SECRET_KEY"] = "test-django-secret-key-for-pytest-2026"
os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"

API_DIR = r"C:\Users\msi\Downloads\travel-platform-mvp-complete\travel-platform-mvp-complete\apps\api"
sys.path.insert(0, API_DIR)

# Use venv site-packages
VENV_PACKAGES = os.path.join(API_DIR, ".venv", "Lib", "site-packages")
if os.path.exists(VENV_PACKAGES):
    sys.path.insert(0, VENV_PACKAGES)

import pytest  # noqa: E402

test_file = os.path.join(API_DIR, "tests", "test_integrations_odoo.py")
ret = pytest.main(["-v", test_file])
sys.exit(ret)
