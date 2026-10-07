import os

PUBLIC_SITE_DIR = r"C:\Users\msi\Downloads\travel-platform-mvp-complete\travel-platform-mvp-complete\apps\public-site"

# 1. Update src/app/actions.ts
ACTIONS_PATH = os.path.join(PUBLIC_SITE_DIR, "src", "app", "actions.ts")
with open(ACTIONS_PATH, "r", encoding="utf-8") as f:
    actions_content = f.read()

if "submitInquiry" not in actions_content:
    inquiry_action = """
export interface InquiryInput {
  name: string;
  email: string;
  phone: string;
  destination?: string;
  tour?: string;
  travelDate?: string;
  guests?: string | number;
  message?: string;
  inquiry_type?: "consultation" | "tour_booking" | "general_support";
}

export async function submitInquiry(input: InquiryInput): Promise<ActionState> {
  const baseUrl = process.env.BACKEND_URL ?? "http://localhost:8000/api/v1";
  try {
    const payload = {
      full_name: input.name,
      email: input.email,
      phone: input.phone,
      destination_slug: input.destination || "",
      tour_slug: input.tour || "",
      travel_date: input.travelDate ? input.travelDate : null,
      guests: Number(input.guests || 1),
      message: input.message || "",
      inquiry_type: input.inquiry_type || (input.tour ? "tour_booking" : "consultation"),
      source: "website",
    };
    const r = await fetch(`${baseUrl}/inquiries/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!r.ok) {
      return { ok: false, message: await messageFrom(r, "Could not submit inquiry.") };
    }
    return { ok: true, message: "Inquiry submitted successfully." };
  } catch (err) {
    return { ok: false, message: "Network connection error. Please try again." };
  }
}
"""
    actions_content += inquiry_action
    with open(ACTIONS_PATH, "w", encoding="utf-8") as f:
        f.write(actions_content)
    print("Updated src/app/actions.ts with submitInquiry.")

# 2. Update src/components/contact/contact-form.tsx
CONTACT_FORM_PATH = os.path.join(PUBLIC_SITE_DIR, "src", "components", "contact", "contact-form.tsx")
with open(CONTACT_FORM_PATH, "r", encoding="utf-8") as f:
    cf_content = f.read()

if "submitInquiry" not in cf_content:
    cf_content = cf_content.replace(
        'import { useLanguage } from "@/lib/i18n/context";',
        'import { useLanguage } from "@/lib/i18n/context";\nimport { submitInquiry } from "@/app/actions";'
    )
    old_submit = """  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSubmitted(true);
    }, 600);
  };"""

    new_submit = """  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    const res = await submitInquiry({
      name: formData.name,
      email: formData.email,
      phone: formData.phone,
      destination: formData.destination,
      travelDate: formData.travelDate,
      guests: formData.guests,
      message: formData.message,
      inquiry_type: "consultation",
    });
    setLoading(false);
    if (res.ok) {
      setSubmitted(true);
    } else {
      alert(res.message);
    }
  };"""
    cf_content = cf_content.replace(old_submit, new_submit)
    with open(CONTACT_FORM_PATH, "w", encoding="utf-8") as f:
        f.write(cf_content)
    print("Updated contact-form.tsx with real submitInquiry.")

# 3. Update src/components/tours/tour-booking-card.tsx
TOUR_CARD_PATH = os.path.join(PUBLIC_SITE_DIR, "src", "components", "tours", "tour-booking-card.tsx")
with open(TOUR_CARD_PATH, "r", encoding="utf-8") as f:
    tc_content = f.read()

if "submitInquiry" not in tc_content:
    tc_content = tc_content.replace(
        'import { useLanguage } from "@/lib/i18n/context";',
        'import { useLanguage } from "@/lib/i18n/context";\nimport { submitInquiry } from "@/app/actions";'
    )
    old_booking = """  const handleBookingSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsBooked(true);
    setTimeout(() => {
      setShowModal(false);
    }, 2500);
  };"""

    new_booking = """  const handleBookingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await submitInquiry({
      name: fullName,
      email: email,
      phone: phone,
      tour: tour.slug,
      travelDate: departureDate,
      guests: adults + children,
      message: `Booking for ${adults} adults, ${children} children. Total: ${totalPrice.toLocaleString()} VND.`,
      inquiry_type: "tour_booking",
    });
    if (res.ok) {
      setIsBooked(true);
      setTimeout(() => {
        setShowModal(false);
      }, 2500);
    } else {
      alert(res.message);
    }
  };"""
    tc_content = tc_content.replace(old_booking, new_booking)
    with open(TOUR_CARD_PATH, "w", encoding="utf-8") as f:
        f.write(tc_content)
    print("Updated tour-booking-card.tsx with real submitInquiry.")
