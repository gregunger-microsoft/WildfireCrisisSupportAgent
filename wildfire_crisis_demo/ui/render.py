"""Markdown rendering helper for Crisis Action Brief."""
from __future__ import annotations

from wildfire_crisis_demo.domain.models import CrisisActionBrief


def brief_to_markdown(
    brief: CrisisActionBrief,
    correlation_id: str,
    timings: dict[str, float],
) -> str:
    lines: list[str] = []
    lines.append("# 🔥 Crisis Action Brief")
    lines.append(f"\n**Correlation ID:** `{correlation_id}`")
    lines.append(f"**Overall Confidence:** {brief.confidence}/100")
    lines.append(f"\n⚠️ *DECISION SUPPORT ONLY — Not command authority*\n")

    lines.append("## Situation Overview")
    lines.append(brief.overview)

    lines.append("\n## Top Risks")
    for i, r in enumerate(brief.risks, 1):
        lines.append(f"{i}. **{r.get('risk', 'N/A')}** — Likelihood: {r.get('likelihood', '?')}, Impact: {r.get('impact', '?')}, Confidence: {r.get('confidence', '?')}")

    lines.append("\n## Courses of Action")
    for coa in brief.coas:
        lines.append(f"\n### {coa.name} (Confidence: {coa.confidence}/100)")
        lines.append(coa.description)
        lines.append("\n**Tradeoffs:**")
        for t in coa.tradeoffs:
            lines.append(f"- {t}")
        lines.append("\n**Risks:**")
        for r in coa.risks:
            lines.append(f"- {r}")

    lines.append("\n## Resource Plan Summary")
    lines.append(brief.resource_plan_summary)

    lines.append("\n## Verification Checklist")
    for item in brief.verification_checklist:
        lines.append(f"- [ ] {item}")

    lines.append("\n## Public Message")
    lines.append(f"> {brief.public_message}")

    lines.append("\n## Internal Message")
    lines.append(brief.internal_message)

    lines.append("\n## Assumptions")
    for a in brief.assumptions:
        lines.append(f"- {a}")

    lines.append("\n## Citations")
    lines.append(", ".join(brief.citations))

    lines.append("\n## Verification Flags")
    for f in brief.verification_flags:
        lines.append(f"- ⚠️ {f}")

    lines.append("\n## Stage Timings")
    for stage, t in timings.items():
        lines.append(f"- {stage}: {t:.3f}s")

    return "\n".join(lines)
