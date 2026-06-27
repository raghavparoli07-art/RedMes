def _normalize(value: str) -> str:
    return (value or "").strip().lower()


def _email_subject(message: str, output_language: str) -> str:
    first_line = next((line.strip() for line in message.splitlines() if line.strip()), "")
    if not first_line:
        return "Subject: Message"

    if _normalize(output_language) == "hindi":
        prefix = "विषय: "
    else:
        prefix = "Subject: "

    clean_line = first_line.rstrip(".!।")
    if len(clean_line) > 56:
        clean_line = clean_line[:53].rstrip() + "..."
    return f"{prefix}{clean_line}"


def _email_greeting(relationship_type: str, output_language: str) -> str:
    language = _normalize(output_language)
    relationship = _normalize(relationship_type)

    if language == "hindi":
        return "नमस्ते,"
    if language == "hinglish":
        return "Hi,"
    if relationship in {"boss_or_senior", "client_or_customer"}:
        return "Hello,"
    return "Hi,"


def _email_signoff(relationship_type: str, output_language: str) -> str:
    language = _normalize(output_language)
    relationship = _normalize(relationship_type)

    if language == "hindi":
        return "धन्यवाद"
    if relationship in {"boss_or_senior", "client_or_customer"}:
        return "Regards"
    return "Thanks"


async def run_channel_formatter(
    chosen_message: str,
    platform: str,
    relationship_type: str,
    output_language: str = "Auto",
) -> dict:
    """
    Formats the chosen rewrite without another LLM call.

    The rewrite itself already comes from the model. This step should be instant:
    it only adapts spacing and light channel conventions.
    """
    message = (chosen_message or "").strip()
    platform_key = _normalize(platform)

    if platform_key == "email":
        formatted_message = "\n\n".join(
            part
            for part in [
                _email_subject(message, output_language),
                _email_greeting(relationship_type, output_language),
                message,
                _email_signoff(relationship_type, output_language),
            ]
            if part
        )
        notes = "Applied local email formatting."
    elif platform_key == "slack":
        formatted_message = message
        notes = "Kept Slack formatting short and direct."
    else:
        formatted_message = " ".join(message.split())
        notes = "Condensed for text message format."

    return {
        "formatted_message": formatted_message,
        "platform": platform,
        "notes": notes,
    }
