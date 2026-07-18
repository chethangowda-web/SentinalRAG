import logging
import re

logger = logging.getLogger(__name__)


_NUMBER_RE = re.compile(r"\b\d+[\.,]?\d*\b")


def detect_contradictions(chunks: list[dict]) -> tuple[bool, str | None]:
    if len(chunks) < 2:
        return False, None

    texts = [c.get("text", "") for c in chunks if c.get("text")]

    number_conflicts = _check_number_conflicts(texts)
    if number_conflicts:
        return True, number_conflicts

    policy_conflicts = _check_policy_conflicts(texts)
    if policy_conflicts:
        return True, policy_conflicts

    return False, None


_CONFLICT_PHRASES = [
    (r"(?:refund|return|policy|period|limit|maximum|minimum|duration|deadline|fee|cost|price|rate)",
     "policy term"),
]


def _check_number_conflicts(texts: list[str]) -> str | None:
    number_map: dict[str, list[str]] = {}
    for text in texts:
        for match in _NUMBER_RE.finditer(text):
            num = match.group()
            context_start = max(0, match.start() - 50)
            context_end = min(len(text), match.end() + 50)
            context = text[context_start:context_end].strip()
            key = f"number:{num}"
            if key not in number_map:
                number_map[key] = []
            number_map[key].append(context)

    for num, contexts in number_map.items():
        unique_contexts = set(c.lower() for c in contexts)
        if len(unique_contexts) > 1:
            return (
                f"Conflicting numbers found: value {num} appears in "
                f"different contexts across chunks (e.g., "
                f"'{contexts[0][:80]}...' vs '{contexts[1][:80]}...')"
            )

    number_contexts: list[tuple[str, str, str]] = []
    for i, text in enumerate(texts):
        for match in _NUMBER_RE.finditer(text):
            num = match.group()
            ctx_start = max(0, match.start() - 50)
            ctx_end = min(len(text), match.end() + 50)
            ctx = text[ctx_start:ctx_end].lower()
            tag = _tag_context(ctx)
            if tag:
                number_contexts.append((num, tag, ctx))

    for i, (num1, tag1, ctx1) in enumerate(number_contexts):
        for num2, tag2, ctx2 in number_contexts[i+1:]:
            if num1 != num2 and tag1 == tag2:
                return (
                    f"Conflicting values for '{tag1}': '{num1}' vs '{num2}' "
                    f"(e.g., '{ctx1[:80]}...' vs '{ctx2[:80]}...')"
                )

    return None


def _tag_context(context: str) -> str | None:
    for pattern, label in _CONFLICT_PHRASES:
        if re.search(pattern, context, re.IGNORECASE):
            return label
    return None


def _check_policy_conflicts(texts: list[str]) -> str | None:
    policy_indicators = [
        (r"(?:no\s+)?refund", "Refund policy"),
        (r"(?:not\s+)?allowed", "Permissions"),
        (r"(?:not\s+)?required", "Requirements"),
        (r"effective\s+date|valid\s+from|expir", "Dates"),
        (r"interest\s+rate|annual\s+percentage|apr", "Rates"),
    ]

    for pattern, label in policy_indicators:
        matches = [(i, re.findall(pattern, t, re.IGNORECASE)) for i, t in enumerate(texts)]
        matches = [(i, m) for i, m in matches if m]
        if len(matches) > 1:
            positive = any(not re.search(r"(?:no |not |excluding )", m[0].lower()) if m else False for _, m in matches)
            negative = any(re.search(r"(?:no |not |excluding )", m[0].lower()) if m else False for _, m in matches)
            if positive and negative:
                reasons = [f"Chunk {i}: '{m[0][:80]}...'" for i, m in matches]
                return f"Conflicting policy detected ({label}): {' vs '.join(reasons)}"

    return None
