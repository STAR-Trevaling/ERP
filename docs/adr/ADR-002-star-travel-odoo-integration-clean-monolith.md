# ADR 002: Star Travels ↔ Odoo 18 Clean Monolith Integration Architecture

## 1. Context
Star Travels (Wanderlust Vietnam) operates a high-performance public platform (Next.js 15 + Django 5.2 + PostGIS). To scale backoffice sales operations and content management without coupling the public runtime to enterprise ERP constraints, we integrate Odoo 18 as the dedicated CRM, CMS Authoring, and Partner Operations backoffice.

## 2. Decision
1. **Decoupled Architecture**:
   - Django PostgreSQL/PostGIS is the **Public Serving Model** (fast reads, spatial indexing `ST_DWithin`, SEO, traveler accounts).
   - Odoo PostgreSQL is the **Authoring & Operational Model** (editorial approval states, CRM lead pipelines, staff notes).
   - Databases are strictly isolated; communication occurs exclusively via versioned HTTP Webhooks and REST endpoints.
2. **Modular Clean Monolith**:
   - Package all Odoo capabilities into 5 decoupled addons:
     - `travel_core`: Domain categories, amenities, system integration configuration.
     - `travel_crm`: Travel-specific CRM extensions (`crm.lead`, `res.partner`, `utm.source`).
     - `travel_cms`: Content authoring and approval workflow for destinations, places, articles.
     - `travel_partner`: Partner onboarding application and staff verification workflow.
     - `travel_integration`: REST Inbound Controller, HMAC-SHA256 verification, Transactional Outbox, Idempotency tracking.
3. **Idempotency & Replay Defense**:
   - Inbound events are tracked in `travel.integration.event` with unique `(source, external_event_id)` constraints.
   - Outbound events use the Transactional Outbox pattern (`travel.integration.outbox`) with exponential backoff retries.
4. **Security**:
   - Inbound requests require Bearer API Key authentication or HMAC-SHA256 signatures (`X-Signature-SHA256`).

## 3. Status
**ACCEPTED** - Approved for Odoo 18 implementation.

## 4. Consequences
- **Positive**: Complete fault isolation (Odoo downtime never affects public website browsing), zero database locking contention between public reads and staff writes, strict auditability.
- **Trade-offs**: Requires maintaining canonical event schemas (`contracts/integration/`) and eventual consistency synchronization.
