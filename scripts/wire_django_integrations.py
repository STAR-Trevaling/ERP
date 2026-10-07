
SETTINGS_PATH = r"C:\Users\msi\Downloads\travel-platform-mvp-complete\travel-platform-mvp-complete\apps\api\config\settings.py"
URLS_PATH = r"C:\Users\msi\Downloads\travel-platform-mvp-complete\travel-platform-mvp-complete\apps\api\config\urls.py"

# Update settings.py
with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

if '"integrations",' not in content:
    content = content.replace('"core",', '"core",\n    "integrations",')
    odoo_cfg = """
# Odoo 18 ERP Integration Settings
ODOO_BASE_URL = os.getenv("ODOO_BASE_URL", "http://localhost:8069")
ODOO_WEBHOOK_SECRET = os.getenv("ODOO_WEBHOOK_SECRET", "star_travels_super_secret_webhook_key_2026")
ODOO_INBOUND_API_KEY = os.getenv("ODOO_INBOUND_API_KEY", "star_travels_inbound_api_token_2026")
"""
    content += odoo_cfg
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated settings.py with integrations app and Odoo settings.")

# Update urls.py
with open(URLS_PATH, "r", encoding="utf-8") as f:
    urls_content = f.read()

if 'include("integrations.urls")' not in urls_content:
    urls_content = urls_content.replace(
        'path("api/v1/", include("core.urls")),',
        'path("api/v1/", include("core.urls")),\n    path("api/v1/", include("integrations.urls")),'
    )
    with open(URLS_PATH, "w", encoding="utf-8") as f:
        f.write(urls_content)
    print("Updated urls.py with integrations.urls.")
