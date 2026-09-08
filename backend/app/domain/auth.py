"""Rules around signup's security questions, used for self-service password
reset (there's no email/SMTP setup yet - CLAUDE.md Phase 3 lists "password
reset" and "email verification" as separate, still-undone items - so a
reset flow that doesn't depend on sending mail is the simplest thing that
actually works today).

The list is fixed (not user-authored questions) so every question has a
reasonably specific, memorable answer - freeform questions too easily end
up as either unanswerable months later or trivially guessable.
"""

SECURITY_QUESTIONS: list[str] = [
    "What was the name of your first pet?",
    "What is your mother's maiden name?",
    "What was the name of your first school?",
    "What city were you born in?",
    "What was your childhood nickname?",
    "What was the make of your first vehicle?",
    "What is your favorite book?",
    "What street did you grow up on?",
]


def normalize_answer(answer: str) -> str:
    """Case/whitespace shouldn't matter for an answer someone is recalling
    from memory - only the content does.
    """
    return answer.strip().lower()
