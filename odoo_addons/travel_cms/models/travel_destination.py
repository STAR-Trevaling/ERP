import re
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TravelDestination(models.Model):
    _name = "travel.destination"
    _description = "Travel Destination"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # noqa: RUF012
    _order = "name"

    name = fields.Char(string="Destination Name", required=True, tracking=True)
    slug = fields.Char(string="Slug", required=True, index=True, tracking=True)
    public_id = fields.Char(
        string="Public Platform UUID",
        index=True,
        copy=False,
        help="UUID mapping to Django Destination.id",
    )
    country = fields.Char(string="Country", default="Vietnam", tracking=True)
    summary = fields.Text(string="Short Summary", help="1-2 sentences for hero & cards")
    description = fields.Html(string="Full Editorial Description", sanitize_style=True)
    image_url = fields.Char(string="Card Image URL")
    hero_image_url = fields.Char(string="Hero Banner Image URL")
    starting_price = fields.Float(string="Starting Price (VND)", digits=(12, 2))
    latitude = fields.Float(string="Latitude", digits=(10, 7))
    longitude = fields.Float(string="Longitude", digits=(10, 7))

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("published", "Published"),
            ("archived", "Archived"),
        ],
        string="Editorial Status",
        default="draft",
        required=True,
        tracking=True,
        index=True,
    )

    version = fields.Integer(string="Content Version", default=1, readonly=True)
    published_at = fields.Datetime(string="Published Date", readonly=True)
    reviewer_id = fields.Many2one("res.users", string="Approved By", readonly=True)
    internal_notes = fields.Text(string="Staff Internal Notes")
    place_ids = fields.One2many(
        "travel.place", "destination_id", string="Attractions & Places"
    )
    place_count = fields.Integer(string="Places Count", compute="_compute_place_count")

    _sql_constraints = [  # noqa: RUF012
        ("slug_uniq", "unique(slug)", "Destination slug must be unique!"),
    ]

    @api.depends("place_ids")
    def _compute_place_count(self):
        for rec in self:
            rec.place_count = len(rec.place_ids)

    @api.onchange("name")
    def _onchange_name(self):
        if self.name and not self.slug:
            self.slug = re.sub(r"[^a-zA-Z0-9]+", "-", self.name.lower()).strip("-")

    def action_submit_review(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(
                    _("Only draft destinations can be submitted for review.")
                )
            rec.write({"state": "in_review"})
        return True

    def action_approve(self):
        for rec in self:
            if rec.state != "in_review":
                raise UserError(
                    _("Only destinations currently in review can be approved.")
                )
            rec.write(
                {
                    "state": "approved",
                    "reviewer_id": self.env.user.id,
                }
            )
        return True

    def action_publish(self):
        for rec in self:
            if rec.state not in ("approved", "published"):
                raise UserError(_("Destination must be approved before publication."))
            rec.write(
                {
                    "state": "published",
                    "published_at": fields.Datetime.now(),
                    "version": rec.version + 1,
                }
            )
            rec._emit_outbox_event("destination.published")
        return True

    def action_archive(self):
        for rec in self:
            rec.write({"state": "archived"})
            rec._emit_outbox_event("destination.archived")
        return True

    def action_request_changes(self):
        for rec in self:
            rec.write({"state": "draft"})
        return True

    def action_reset_draft(self):
        for rec in self:
            rec.write({"state": "draft"})
        return True

    def _emit_outbox_event(self, event_type):
        """Helper to create transactional outbox event if travel_integration is available."""
        if "travel.integration.outbox" in self.env:
            for rec in self:
                payload = {
                    "content_type": "destination",
                    "id": rec.public_id or str(uuid.uuid4()),
                    "slug": rec.slug,
                    "version": rec.version,
                    "published_at": rec.published_at.isoformat()
                    if rec.published_at
                    else fields.Datetime.now().isoformat(),
                    "destination": {
                        "name": rec.name,
                        "country": rec.country or "",
                        "summary": rec.summary or "",
                        "description": rec.description or "",
                        "image_url": rec.image_url or "",
                        "hero_image_url": rec.hero_image_url or "",
                        "starting_price": rec.starting_price,
                        "latitude": rec.latitude,
                        "longitude": rec.longitude,
                    },
                }
                self.env["travel.integration.outbox"].create_event(
                    event_type=event_type,
                    payload=payload,
                    source="odoo",
                )
