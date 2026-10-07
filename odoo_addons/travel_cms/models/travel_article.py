import re
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class TravelArticle(models.Model):
    _name = "travel.article"
    _description = "Travel Editorial Article & Story"
    _inherit = ["mail.thread", "mail.activity.mixin"]  # noqa: RUF012
    _order = "published_at desc, create_date desc"

    title = fields.Char(string="Article Title", required=True, tracking=True)
    slug = fields.Char(string="Slug", required=True, index=True, tracking=True)
    public_id = fields.Char(
        string="Public Platform UUID",
        index=True,
        copy=False,
        help="UUID mapping to Django Article.id",
    )
    excerpt = fields.Text(string="Excerpt", help="Brief introductory summary")
    body = fields.Html(
        string="Article Body Content", required=True, sanitize_style=True
    )
    cover_image = fields.Char(string="Cover Image URL")

    destination_id = fields.Many2one(
        "travel.destination", string="Related Destination", ondelete="set null"
    )
    place_id = fields.Many2one(
        "travel.place", string="Related Place", ondelete="set null"
    )

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
    author_id = fields.Many2one(
        "res.users", string="Author", default=lambda self: self.env.user
    )
    internal_notes = fields.Text(string="Staff Internal Notes")

    _sql_constraints = [  # noqa: RUF012
        ("slug_uniq", "unique(slug)", "Article slug must be unique!"),
    ]

    @api.onchange("title")
    def _onchange_title(self):
        if self.title and not self.slug:
            self.slug = re.sub(r"[^a-zA-Z0-9]+", "-", self.title.lower()).strip("-")

    def action_submit_review(self):
        for rec in self:
            if rec.state != "draft":
                raise UserError(_("Only draft articles can be submitted for review."))
            rec.write({"state": "in_review"})
        return True

    def action_approve(self):
        for rec in self:
            if rec.state != "in_review":
                raise UserError(_("Only articles currently in review can be approved."))
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
                raise UserError(_("Article must be approved before publication."))
            rec.write(
                {
                    "state": "published",
                    "published_at": fields.Datetime.now(),
                    "version": rec.version + 1,
                }
            )
            rec._emit_outbox_event("article.published")
        return True

    def action_archive(self):
        for rec in self:
            rec.write({"state": "archived"})
            rec._emit_outbox_event("article.archived")
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
                    "content_type": "article",
                    "id": rec.public_id or str(uuid.uuid4()),
                    "slug": rec.slug,
                    "version": rec.version,
                    "published_at": rec.published_at.isoformat()
                    if rec.published_at
                    else fields.Datetime.now().isoformat(),
                    "article": {
                        "title": rec.title,
                        "excerpt": rec.excerpt or "",
                        "body": rec.body or "",
                        "cover_image": rec.cover_image or "",
                        "destination_slug": rec.destination_id.slug
                        if rec.destination_id
                        else None,
                        "place_slug": rec.place_id.slug if rec.place_id else None,
                    },
                }
                self.env["travel.integration.outbox"].create_event(
                    event_type=event_type,
                    payload=payload,
                    source="odoo",
                )
