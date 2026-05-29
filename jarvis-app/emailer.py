"""Email drafting — NEVER sends. Builds a general or news-tailored draft and
supports copy / .eml / CSV export. Optional Anthropic tailoring if a key is set."""
import os

GENERAL_TEMPLATE = """Dear {first_name},

I'm [Your Name], [Your Title] at A.G.P. / Alliance Global Partners, a full-service \
investment bank and broker-dealer active in the small- and micro-cap equity capital \
markets. We work with public companies like {company} across the full ECM toolkit — \
IPOs and follow-on offerings, registered directs and PIPEs, ATM programs, and equity \
lines (ELOCs) — alongside research and sales coverage.

I'd welcome a brief introductory call to share how we're helping companies of \
{company}'s size access capital in today's market and to hear your priorities for the \
year ahead.

Would you have 15-20 minutes over the next couple of weeks? Happy to work around your \
calendar.

Best regards,
[Your Name] - [Title] - A.G.P. / Alliance Global Partners - [Phone] - [Email]
"""

SUBJECT = "A.G.P. — equity capital markets coverage for {company}"
COMPLIANCE = ("Drafts for review only. Outbound communications are subject to A.G.P. "
              "supervisory review under FINRA Rule 2210 before sending.")


def _first(name):
    return (name or "there").split(" ")[0]


def draft_general(company, contact_name):
    return SUBJECT.format(company=company), GENERAL_TEMPLATE.format(
        first_name=_first(contact_name), company=company)


def draft_tailored(company, contact_name, latest_news=None, last_financing=None):
    """Anthropic if ANTHROPIC_API_KEY is set; otherwise merge news into template."""
    if os.getenv("ANTHROPIC_API_KEY"):
        try:
            return _anthropic_tailored(company, contact_name, latest_news, last_financing)
        except Exception:  # noqa: BLE001 — fall back silently to template merge
            pass
    opener = ""
    if latest_news:
        opener = f"I saw that {company} recently {latest_news.strip().rstrip('.')}. "
    elif last_financing:
        opener = f"I noticed {company}'s recent {last_financing}. "
    subj, body = draft_general(company, contact_name)
    body = body.replace("I'm [Your Name]", opener + "I'm [Your Name]", 1)
    return subj, body


def _anthropic_tailored(company, contact_name, latest_news, last_financing):
    import anthropic
    client = anthropic.Anthropic()
    prompt = (f"Write a concise, compliant ECM outreach email opener (2-3 sentences) for "
              f"{contact_name} at {company}. Context — latest news: {latest_news}; recent "
              f"financing: {last_financing}. Then continue with a 15-20 minute intro-call "
              f"ask. Sign as [Your Name], A.G.P. / Alliance Global Partners. No claims, no "
              f"promises of returns.")
    msg = client.messages.create(model="claude-sonnet-4-5", max_tokens=600,
                                 messages=[{"role": "user", "content": prompt}])
    return SUBJECT.format(company=company), msg.content[0].text


def to_eml(to_addr, subject, body):
    return (f"To: {to_addr or ''}\r\nSubject: {subject}\r\n"
            f"X-Note: DRAFT - review only, do not auto-send\r\n\r\n{body}")
