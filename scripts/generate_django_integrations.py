import os

TARGET_DIR = r"C:\Users\msi\Downloads\travel-platform-mvp-complete\travel-platform-mvp-complete\apps\api\integrations"
os.makedirs(TARGET_DIR, exist_ok=True)

# 1. __init__.py
with open(os.path.join(TARGET_DIR, "__init__.py"), "w", encoding="utf-8") as f:
    f.write('default_app_config = "integrations.apps.IntegrationsConfig"\n')

# 2. apps.py
with open(os.path.join(TARGET_DIR, "apps.py"), "w", encoding="utf-8") as f:
    f.write('''from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "integrations"
    verbose_name = "STAR Travels Integrations & Webhooks"
''')

# 3. models.py
with open(os.path.join(TARGET_DIR, "models.py"), "w", encoding="utf-8") as f:
    f.write('''import uuid
from django.db import models
from django.utils import timezone


class Inquiry(models.Model):
    class InquiryType(models.TextChoices):
        CONSULTATION = "consultation", "Destination Consultation"
        TOUR_BOOKING = "tour_booking", "Tour / Experience Booking"
        GENERAL_SUPPORT = "general_support", "General Support"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Sync"
        SYNCED = "synced", "Synced to Odoo CRM"
        FAILED = "failed", "Sync Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=180)
    email = models.EmailField()
    phone = models.CharField(max_length=40)
    destination_slug = models.CharField(max_length=180, blank=True)
    tour_slug = models.CharField(max_length=180, blank=True)
    travel_date = models.DateField(null=True, blank=True)
    guests = models.PositiveIntegerField(default=1)
    message = models.TextField(blank=True)
    inquiry_type = models.CharField(
        max_length=30, choices=InquiryType.choices, default=InquiryType.CONSULTATION, db_index=True
    )
    source = models.CharField(max_length=50, default="website", db_index=True)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    odoo_lead_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name_plural = "Inquiries"

    def __str__(self):
        return f"{self.full_name} ({self.inquiry_type}) - {self.phone}"


class IntegrationOutbox(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending Delivery"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Permanently Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_id = models.CharField(max_length=64, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    event_version = models.PositiveSmallIntegerField(default=1)
    source = models.CharField(max_length=50, default="public-platform")
    payload = models.JSONField()

    state = models.CharField(
        max_length=20, choices=State.choices, default=State.PENDING, db_index=True
    )
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=5)
    next_retry_at = models.DateTimeField(default=timezone.now, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    http_status = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=("state", "next_retry_at"), name="outbox_state_retry_idx")
        ]

    def __str__(self):
        return f"Outbox [{self.event_type}] {self.event_id} ({self.state})"


class IntegrationEvent(models.Model):
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=50, db_index=True)
    external_event_id = models.CharField(max_length=100, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    event_version = models.PositiveSmallIntegerField(default=1)
    payload_hash = models.CharField(max_length=64, blank=True)

    state = models.CharField(
        max_length=20, choices=State.choices, default=State.PENDING, db_index=True
    )
    raw_payload = models.JSONField()
    response_json = models.JSONField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-received_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("source", "external_event_id"), name="unique_source_external_event"
            )
        ]

    def __str__(self):
        return f"Inbound [{self.source}] {self.event_type} - {self.external_event_id}"
''')

# 4. serializers.py
with open(os.path.join(TARGET_DIR, "serializers.py"), "w", encoding="utf-8") as f:
    f.write('''from rest_framework import serializers
from .models import Inquiry


class InquiryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inquiry
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "destination_slug",
            "tour_slug",
            "travel_date",
            "guests",
            "message",
            "inquiry_type",
            "source",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class OdooWebhookEventSerializer(serializers.Serializer):
    event_id = serializers.CharField(required=True)
    event_type = serializers.CharField(required=True)
    event_version = serializers.IntegerField(default=1)
    source = serializers.CharField(default="odoo")
    occurred_at = serializers.CharField(required=False)
    data = serializers.DictField(required=True)
''')

# 5. tasks.py (Celery)
with open(os.path.join(TARGET_DIR, "tasks.py"), "w", encoding="utf-8") as f:
    f.write('''import hashlib
import hmac
import json
import logging
import urllib.request
import urllib.error
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from .models import IntegrationOutbox, Inquiry

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=5)
def dispatch_outbox_event(self, outbox_id):
    """
    Asynchronously dispatch a single Outbox event to Odoo with HMAC signature & exponential backoff.
    """
    try:
        outbox = IntegrationOutbox.objects.get(id=outbox_id)
    except IntegrationOutbox.DoesNotExist:
        logger.error(f"Outbox record {outbox_id} does not exist.")
        return False

    if outbox.state == IntegrationOutbox.State.DELIVERED:
        return True

    odoo_base = getattr(settings, "ODOO_BASE_URL", "http://localhost:8069").rstrip("/")
    secret = getattr(settings, "ODOO_WEBHOOK_SECRET", "star_travels_super_secret_webhook_key_2026")

    endpoint_map = {
        "inquiry.created": f"{odoo_base}/api/v1/travel/inquiry",
        "lead.created": f"{odoo_base}/api/v1/travel/inquiry",
        "partner.application.created": f"{odoo_base}/api/v1/travel/partner-application",
    }
    url = endpoint_map.get(outbox.event_type, f"{odoo_base}/api/v1/travel/inquiry")

    raw_body = json.dumps(outbox.payload).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "StarTravels-Django/1.0",
        "X-Signature-SHA256": signature,
        "X-Event-Type": outbox.event_type,
        "X-Event-ID": outbox.event_id,
        "Idempotency-Key": outbox.event_id,
    }

    req = urllib.request.Request(url, data=raw_body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.getcode()
            resp_body = resp.read().decode("utf-8")
            if 200 <= status_code < 300:
                outbox.state = IntegrationOutbox.State.DELIVERED
                outbox.delivered_at = timezone.now()
                outbox.http_status = status_code
                outbox.last_error = ""
                outbox.save(update_fields=["state", "delivered_at", "http_status", "last_error"])

                # Update linked Inquiry status if available
                try:
                    resp_data = json.loads(resp_body)
                    inquiry_id = outbox.payload.get("data", {}).get("inquiry_id")
                    if inquiry_id:
                        inquiry = Inquiry.objects.filter(id=inquiry_id).first()
                        if inquiry:
                            inquiry.status = Inquiry.Status.SYNCED
                            inquiry.odoo_lead_id = resp_data.get("lead_id")
                            inquiry.save(update_fields=["status", "odoo_lead_id"])
                except Exception as update_err:
                    logger.warning(f"Could not update inquiry status: {update_err}")

                logger.info(f"Successfully dispatched Outbox Event {outbox.event_id} to Odoo ({status_code})")
                return True
    except urllib.error.HTTPError as e:
        err_msg = f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"
        status_code = e.code
    except Exception as e:
        err_msg = f"Network error: {str(e)}"
        status_code = 0

    # Failure handling
    new_retries = self.request.retries + 1
    outbox.retry_count = new_retries
    outbox.last_error = err_msg
    outbox.http_status = status_code

    if new_retries >= outbox.max_retries:
        outbox.state = IntegrationOutbox.State.FAILED
        outbox.save(update_fields=["state", "retry_count", "last_error", "http_status"])
        logger.error(f"Permanently failed Outbox Event {outbox.event_id}: {err_msg}")
    else:
        # Exponential backoff countdown: 10s, 30s, 90s, 270s
        countdown = 10 * (3 ** (new_retries - 1))
        outbox.next_retry_at = timezone.now() + timezone.timedelta(seconds=countdown)
        outbox.save(update_fields=["retry_count", "next_retry_at", "last_error", "http_status"])
        logger.warning(f"Retrying Outbox Event {outbox.event_id} in {countdown}s: {err_msg}")
        raise self.retry(exc=Exception(err_msg), countdown=countdown)


@shared_task
def sweep_pending_outbox():
    """Periodic task to pick up pending outbox events that are due for retry."""
    now = timezone.now()
    pending = IntegrationOutbox.objects.filter(
        state=IntegrationOutbox.State.PENDING, next_retry_at__lte=now
    )[:50]
    for rec in pending:
        dispatch_outbox_event.delay(str(rec.id))
    return len(pending)
''')

# 6. views.py
with open(os.path.join(TARGET_DIR, "views.py"), "w", encoding="utf-8") as f:
    f.write('''import hashlib
import hmac
import json
import logging
import uuid
from django.conf import settings
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from content.models import Article
from destinations.models import Destination
from partners.models import PartnerApplication, PartnerOrganization
from places.models import Category, Place
from .models import Inquiry, IntegrationEvent, IntegrationOutbox
from .serializers import InquiryCreateSerializer, OdooWebhookEventSerializer
from .tasks import dispatch_outbox_event

logger = logging.getLogger(__name__)


class InquiryCreateView(APIView):
    """
    Public API endpoint for inquiries, tour consultations, and bookings.
    Persists Inquiry, creates Outbox event, and enqueues Celery dispatch to Odoo CRM.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = InquiryCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        inquiry = serializer.save()

        # Build canonical payload envelope
        event_id = str(uuid.uuid4())
        envelope = {
            "event_id": event_id,
            "event_type": "inquiry.created",
            "event_version": 1,
            "source": inquiry.source or "website",
            "occurred_at": timezone.now().isoformat(),
            "data": {
                "inquiry_id": str(inquiry.id),
                "customer": {
                    "name": inquiry.full_name,
                    "email": inquiry.email,
                    "phone": inquiry.phone,
                    "identity_provider": inquiry.source,
                },
                "interest": {
                    "type": inquiry.inquiry_type,
                    "destination_slug": inquiry.destination_slug,
                    "tour_slug": inquiry.tour_slug,
                    "travel_date": str(inquiry.travel_date) if inquiry.travel_date else None,
                    "traveler_count": inquiry.guests,
                    "message": inquiry.message,
                },
                "source_metadata": {
                    "channel": inquiry.source,
                    "ip": request.META.get("REMOTE_ADDR"),
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                },
            },
        }

        outbox = IntegrationOutbox.objects.create(
            event_id=event_id,
            event_type="inquiry.created",
            event_version=1,
            source=inquiry.source,
            payload=envelope,
            state=IntegrationOutbox.State.PENDING,
        )

        # Trigger Celery asynchronous dispatch
        try:
            dispatch_outbox_event.delay(str(outbox.id))
        except Exception as e:
            logger.warning(f"Could not immediately dispatch Celery task: {e}")

        return Response(
            {
                "success": True,
                "inquiry_id": str(inquiry.id),
                "event_id": event_id,
                "message": "Inquiry successfully recorded and queued for CRM processing.",
            },
            status=status.HTTP_201_CREATED,
        )


class OdooWebhookReceiverView(APIView):
    """
    Inbound Webhook receiver from Odoo 18 CMS (destination.published, place.published, article.published, partner.approved).
    Protected by HMAC-SHA256 signature and Idempotency key.
    """
    permission_classes = [AllowAny]

    def _verify_hmac(self, request):
        secret = getattr(settings, "ODOO_WEBHOOK_SECRET", "star_travels_super_secret_webhook_key_2026")
        sig_header = request.headers.get("X-Signature-SHA256")
        if not sig_header:
            return False

        raw_body = request.body
        computed_sig = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig_header, computed_sig)

    def post(self, request, *args, **kwargs):
        if not self._verify_hmac(request):
            return Response(
                {
                    "type": "https://star-travels.com/errors/unauthorized",
                    "title": "Unauthorized",
                    "status": 401,
                    "detail": "Invalid or missing HMAC-SHA256 signature in X-Signature-SHA256 header.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = OdooWebhookEventSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        event_data = serializer.validated_data
        event_id = event_data["event_id"]
        event_type = event_data["event_type"]
        source = event_data.get("source", "odoo")
        data = event_data["data"]

        # 1. Idempotency Check
        raw_hash = hashlib.sha256(request.body).hexdigest()
        existing_event = IntegrationEvent.objects.filter(
            source=source, external_event_id=event_id
        ).first()

        if existing_event:
            if existing_event.state == IntegrationEvent.State.PROCESSED and existing_event.response_json:
                logger.info(f"Idempotent replay detected for event {event_id}. Returning cached response.")
                return Response(existing_event.response_json, status=status.HTTP_200_OK)
            event_record = existing_event
        else:
            event_record = IntegrationEvent.objects.create(
                source=source,
                external_event_id=event_id,
                event_type=event_type,
                event_version=event_data.get("event_version", 1),
                payload_hash=raw_hash,
                raw_payload=request.data,
                state=IntegrationEvent.State.PENDING,
            )

        # 2. Dispatch domain logic
        try:
            result = self._process_domain_event(event_type, data)
            event_record.state = IntegrationEvent.State.PROCESSED
            event_record.processed_at = timezone.now()
            event_record.response_json = result
            event_record.save(update_fields=["state", "processed_at", "response_json"])
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error processing Odoo event {event_id}: {e}")
            event_record.state = IntegrationEvent.State.FAILED
            event_record.last_error = str(e)
            event_record.save(update_fields=["state", "last_error"])
            return Response(
                {
                    "type": "https://star-travels.com/errors/internal_error",
                    "title": "Processing Error",
                    "status": 500,
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _process_domain_event(self, event_type, data):
        """Map Odoo CMS/Partner authoring payload into Django serving models."""
        if event_type in ("destination.published", "destination.updated"):
            dest_info = data.get("destination") or data
            slug = data.get("slug") or dest_info.get("slug")
            name = dest_info.get("name", "")
            lat = float(dest_info.get("latitude") or 0.0)
            lng = float(dest_info.get("longitude") or 0.0)
            center = Point(lng, lat, srid=4326) if (lat and lng) else None

            dest, created = Destination.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "country": dest_info.get("country", "Việt Nam"),
                    "summary": dest_info.get("summary", ""),
                    "description": dest_info.get("description", ""),
                    "image_url": dest_info.get("image_url", ""),
                    "hero_image_url": dest_info.get("hero_image_url", ""),
                    "starting_price": dest_info.get("starting_price"),
                    "center": center,
                    "is_published": True,
                },
            )
            return {"status": "synced", "model": "Destination", "slug": dest.slug, "created": created}

        elif event_type in ("place.published", "place.updated"):
            place_info = data.get("place") or data
            slug = data.get("slug") or place_info.get("slug")
            name = place_info.get("name", "")
            dest_slug = place_info.get("destination_slug")
            cat_slug = place_info.get("category_slug")

            dest = Destination.objects.filter(slug=dest_slug).first()
            category = Category.objects.filter(slug=cat_slug).first()

            lat = float(place_info.get("latitude") or 0.0)
            lng = float(place_info.get("longitude") or 0.0)
            location = Point(lng, lat, srid=4326)

            if not dest or not category:
                raise ValueError(f"Destination '{dest_slug}' or Category '{cat_slug}' not found.")

            place, created = Place.objects.update_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "destination": dest,
                    "category": category,
                    "short_description": place_info.get("short_description", ""),
                    "description": place_info.get("description", ""),
                    "image_url": place_info.get("image_url", ""),
                    "overlay_image_url": place_info.get("overlay_image_url", ""),
                    "address": place_info.get("address", ""),
                    "website_url": place_info.get("website_url", ""),
                    "location": location,
                    "average_rating": place_info.get("average_rating", 0.0),
                    "review_count": place_info.get("review_count", 0),
                    "is_published": True,
                },
            )
            return {"status": "synced", "model": "Place", "slug": place.slug, "created": created}

        elif event_type in ("article.published", "article.updated"):
            art_info = data.get("article") or data
            slug = data.get("slug") or art_info.get("slug")
            dest_slug = art_info.get("destination_slug")
            dest = Destination.objects.filter(slug=dest_slug).first() if dest_slug else None

            article, created = Article.objects.update_or_create(
                slug=slug,
                defaults={
                    "title": art_info.get("title", ""),
                    "excerpt": art_info.get("excerpt", ""),
                    "body": art_info.get("body", ""),
                    "cover_image": art_info.get("cover_image", ""),
                    "destination": dest,
                    "status": Article.Status.PUBLISHED,
                    "published_at": timezone.now(),
                },
            )
            return {"status": "synced", "model": "Article", "slug": article.slug, "created": created}

        elif event_type in ("partner.approved",):
            app_id = data.get("application_id")
            app = PartnerApplication.objects.filter(id=app_id).first() if app_id else None
            if app:
                app.status = PartnerApplication.Status.APPROVED
                app.save(update_fields=["status"])
                org = getattr(app, "organization", None)
                if org:
                    org.is_active = True
                    org.save(update_fields=["is_active"])
                return {"status": "synced", "model": "PartnerApplication", "id": str(app.id), "approved": True}
            return {"status": "acknowledged", "detail": f"Application {app_id} not found."}

        return {"status": "ignored", "event_type": event_type}
''')

# 7. urls.py
with open(os.path.join(TARGET_DIR, "urls.py"), "w", encoding="utf-8") as f:
    f.write('''from django.urls import path
from .views import InquiryCreateView, OdooWebhookReceiverView

urlpatterns = [
    path("inquiries/", InquiryCreateView.as_view(), name="inquiry-create"),
    path("integrations/v1/odoo/events", OdooWebhookReceiverView.as_view(), name="odoo-webhook-events"),
]
''')

print("Integrations app successfully created in Django API.")
