import uuid
import xmlrpc.client

url = "http://localhost:8069"
db = "odoo_travel"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, "admin", "admin", {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

test_slug = f"son-tra-{uuid.uuid4().hex[:6]}"

# 1. Create a draft destination
dest_id = models.execute_kw(
    db,
    uid,
    "admin",
    "travel.destination",
    "create",
    [
        {
            "name": f"Bán đảo Sơn Trà Test {test_slug}",
            "slug": test_slug,
            "country": "Đà Nẵng, Việt Nam",
            "latitude": 16.1167,
            "longitude": 108.2833,
        }
    ],
)

# 2. Workflow: Submit -> Approve -> Publish
models.execute_kw(
    db, uid, "admin", "travel.destination", "action_submit_review", [[dest_id]]
)
models.execute_kw(db, uid, "admin", "travel.destination", "action_approve", [[dest_id]])
models.execute_kw(db, uid, "admin", "travel.destination", "action_publish", [[dest_id]])

# 3. Check outbox
outbox_ids = models.execute_kw(
    db,
    uid,
    "admin",
    "travel.integration.outbox",
    "search",
    [[("event_type", "=", "destination.published")]],
    {"order": "id desc", "limit": 1},
)
records = models.execute_kw(
    db,
    uid,
    "admin",
    "travel.integration.outbox",
    "read",
    [outbox_ids, ["event_id", "event_type", "state", "payload"]],
)
print("Published destination ID:", dest_id)
print("Outbox records created:", len(records))
if records:
    print(
        "Latest Outbox Event:",
        records[0]["event_type"],
        records[0]["state"],
        "ID:",
        records[0]["event_id"],
    )
