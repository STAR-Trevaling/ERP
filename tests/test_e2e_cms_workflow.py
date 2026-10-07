import uuid

import pytest


@pytest.mark.e2e
def test_e2e_cms_destination_editorial_lifecycle_and_outbox(odoo_rpc):
    """
    Test end-to-end CMS editorial workflow:
    1. Create Destination in Draft.
    2. Workflow transitions: submit_review -> approve -> publish.
    3. Assert version bumped from 1 to 2.
    4. Assert Outbox event 'destination.published' created with full payload.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    test_slug = f"test-e2e-dest-{unique_suffix}"
    test_name = f"Bán đảo E2E {unique_suffix.upper()}"

    # 1. Create Destination
    dest_id = odoo_rpc.execute(
        "travel.destination",
        "create",
        [{
            "name": test_name,
            "slug": test_slug,
            "country": "Việt Nam",
            "latitude": 15.8801,
            "longitude": 108.3380,
            "summary": "Tóm tắt kiểm thử E2E tự động.",
            "starting_price": 500000.0,
        }],
    )
    assert dest_id, "Failed to create destination"

    dest_data = odoo_rpc.execute("travel.destination", "read", [dest_id], ["state", "version"])[0]
    assert dest_data["state"] == "draft"
    assert dest_data["version"] == 1

    # 2. Workflow transitions
    odoo_rpc.execute("travel.destination", "action_submit_review", [dest_id])
    state_review = odoo_rpc.execute("travel.destination", "read", [dest_id], ["state"])[0]["state"]
    assert state_review == "in_review"

    odoo_rpc.execute("travel.destination", "action_approve", [dest_id])
    state_approved = odoo_rpc.execute("travel.destination", "read", [dest_id], ["state"])[0]["state"]
    assert state_approved == "approved"

    odoo_rpc.execute("travel.destination", "action_publish", [dest_id])
    dest_published = odoo_rpc.execute("travel.destination", "read", [dest_id], ["state", "version", "published_at"])[0]
    assert dest_published["state"] == "published"
    assert dest_published["version"] == 2
    assert dest_published["published_at"] is not False

    # 3. Assert Transactional Outbox Event
    outbox_ids = odoo_rpc.execute(
        "travel.integration.outbox",
        "search",
        [("event_type", "=", "destination.published")],
        {"order": "id desc", "limit": 1},
    )
    assert outbox_ids, "No outbox event found for destination.published"

    outbox_event = odoo_rpc.execute(
        "travel.integration.outbox",
        "read",
        outbox_ids,
        ["event_id", "event_type", "state", "payload"],
    )[0]
    assert outbox_event["event_type"] == "destination.published"
    assert test_slug in outbox_event["payload"]
    assert outbox_event["state"] in ("pending", "processing", "done")


@pytest.mark.e2e
def test_e2e_cms_article_editorial_lifecycle_and_outbox(odoo_rpc):
    """
    Test Article publishing lifecycle and outbox emission:
    Draft -> Review -> Approve -> Publish -> outbox 'article.published'.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    test_slug = f"test-e2e-article-{unique_suffix}"
    test_title = f"Cẩm nang du lịch E2E {unique_suffix.upper()}"

    article_id = odoo_rpc.execute(
        "travel.article",
        "create",
        [{
            "title": test_title,
            "slug": test_slug,
            "excerpt": "Tóm tắt cẩm nang E2E",
            "body": "<p>Nội dung chi tiết cẩm nang du lịch kiểm thử.</p>",
        }],
    )
    assert article_id

    # Transitions
    odoo_rpc.execute("travel.article", "action_submit_review", [article_id])
    odoo_rpc.execute("travel.article", "action_approve", [article_id])
    odoo_rpc.execute("travel.article", "action_publish", [article_id])

    article_published = odoo_rpc.execute("travel.article", "read", [article_id], ["state", "version"])[0]
    assert article_published["state"] == "published"
    assert article_published["version"] == 2

    # Check outbox
    outbox_ids = odoo_rpc.execute(
        "travel.integration.outbox",
        "search",
        [("event_type", "=", "article.published")],
        {"order": "id desc", "limit": 1},
    )
    assert outbox_ids
    outbox_event = odoo_rpc.execute(
        "travel.integration.outbox",
        "read",
        outbox_ids,
        ["event_type", "payload"],
    )[0]
    assert outbox_event["event_type"] == "article.published"
    assert test_slug in outbox_event["payload"]


@pytest.mark.e2e
def test_e2e_cms_place_editorial_lifecycle_and_outbox(odoo_rpc):
    """
    Test Place editorial lifecycle:
    Draft -> Review -> Approve -> Publish -> outbox 'place.published'.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    test_slug = f"test-e2e-place-{unique_suffix}"
    test_name = f"Địa điểm E2E {unique_suffix.upper()}"

    # Get or create destination & category
    cat_ids = odoo_rpc.execute("travel.category", "search", [], {"limit": 1})
    if not cat_ids:
        cat_id = odoo_rpc.execute(
            "travel.category",
            "create",
            [{"name": "Điểm tham quan E2E", "slug": f"cat-e2e-{unique_suffix}"}],
        )
    else:
        cat_id = cat_ids[0]

    dest_id = odoo_rpc.execute(
        "travel.destination",
        "create",
        [{
            "name": f"Điểm đến mẹ {unique_suffix}",
            "slug": f"dest-parent-{unique_suffix}",
            "country": "Việt Nam",
            "latitude": 16.0544,
            "longitude": 108.2022,
        }],
    )

    place_id = odoo_rpc.execute(
        "travel.place",
        "create",
        [{
            "name": test_name,
            "slug": test_slug,
            "destination_id": dest_id,
            "category_id": cat_id,
            "latitude": 16.0600,
            "longitude": 108.2100,
            "short_description": "Mô tả ngắn địa điểm E2E",
        }],
    )
    assert place_id

    # Transitions
    odoo_rpc.execute("travel.place", "action_submit_review", [place_id])
    odoo_rpc.execute("travel.place", "action_approve", [place_id])
    odoo_rpc.execute("travel.place", "action_publish", [place_id])

    place_data = odoo_rpc.execute("travel.place", "read", [place_id], ["state", "version"])[0]
    assert place_data["state"] == "published"
    assert place_data["version"] == 2

    # Verify Outbox
    outbox_ids = odoo_rpc.execute(
        "travel.integration.outbox",
        "search",
        [("event_type", "=", "place.published")],
        {"order": "id desc", "limit": 1},
    )
    assert outbox_ids
    outbox_event = odoo_rpc.execute(
        "travel.integration.outbox",
        "read",
        outbox_ids,
        ["event_type", "payload"],
    )[0]
    assert outbox_event["event_type"] == "place.published"
    assert test_slug in outbox_event["payload"]


@pytest.mark.e2e
def test_e2e_partner_application_approval_workflow(odoo_rpc):
    """
    Test B2B Partner Onboarding Workflow:
    Submitted -> Under Review -> Approved -> res.partner created.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    business_name = f"Công ty Du lịch E2E {unique_suffix.upper()}"
    email = f"partner_{unique_suffix}@travelcorp.vn"

    app_id = odoo_rpc.execute(
        "travel.partner.application",
        "create",
        [{
            "business_name": business_name,
            "email": email,
            "phone": "0987654321",
            "website": "https://travelcorp.vn",
            "message": "Đăng ký đối tác vận chuyển E2E.",
        }],
    )
    assert app_id

    # Initial state
    app_data = odoo_rpc.execute("travel.partner.application", "read", [app_id], ["state"])[0]
    assert app_data["state"] == "submitted"

    # Start review
    odoo_rpc.execute("travel.partner.application", "action_start_review", [app_id])
    app_data_review = odoo_rpc.execute("travel.partner.application", "read", [app_id], ["state"])[0]
    assert app_data_review["state"] == "under_review"

    # Approve -> should generate res.partner
    odoo_rpc.execute("travel.partner.application", "action_approve", [app_id])
    app_data_approved = odoo_rpc.execute(
        "travel.partner.application",
        "read",
        [app_id],
        ["state", "partner_id", "organization_slug"],
    )[0]
    assert app_data_approved["state"] == "approved"
    assert app_data_approved["partner_id"] is not False

    partner_id = app_data_approved["partner_id"][0]
    partner_data = odoo_rpc.execute(
        "res.partner",
        "read",
        [partner_id],
        ["name", "email", "is_company"],
    )[0]
    assert partner_data["name"] == business_name
    assert partner_data["email"] == email
    assert partner_data["is_company"] is True

