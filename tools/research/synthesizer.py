from __future__ import annotations
from tools.research.models import ResearchEvidence, ResearchPlan, ResearchReport
from tools.research.source_policy import SourcePolicy
from tools.search.models import EvidenceItem, FetchedPage

class ResearchSynthesizer:
    def __init__(self, source_policy: SourcePolicy | None = None) -> None:
        self.source_policy = source_policy or SourcePolicy()

    def synthesize(self, plan: ResearchPlan, evidence: list[ResearchEvidence]) -> ResearchReport:
        findings = self._findings(evidence)
        source_urls = self._source_urls(evidence)
        caveats = self._caveats(plan, evidence, source_urls)
        confidence = self._confidence(source_urls, caveats)

        if findings:
            answer = "\n".join(f"- {finding}" for finding in findings[:8])
        else:
            answer = "No source evidence was available, so no supported research answer could be generated."

        return ResearchReport(
            original_query=plan.original_query,
            question_type=plan.question_type,
            answer=answer,
            confidence=confidence,
            caveats=caveats,
            source_urls=source_urls,
        )
    
    def render(self, report: ResearchReport) -> str:
        lines = [
            "Short answer:",
            report.answer,
            "",
            "Key findings:",
        ]

        if report.answer.startswith("- "):
            lines.extend(report.answer.splitlines())
        else:
            lines.append(f"_ {report.answer}")

        lines.extend(
            [
                "",
                "Details:",
                report.answer,
                "",
                "Confidence:",
                report.confidence,
            ]
        )

        if report.caveats:
            lines.extend(
                [
                    "",
                    "Caveats:",
                ]
            )
            lines.extend(f"- {caveat}" for caveat in report.caveats)

        lines.extend(["", "Sources:"])
        if report.source_urls:
            lines.extend(f"- {url}" for url in report.source_urls)
        else:
            lines.append("- No sources were available.")

        return "\n".join(lines)
    
    def _findings(self, evidence: list[ResearchEvidence]) -> list[str]:
        findings: list[str] = []
        seen: set[str] = set()

        for item in evidence:
            if item.pack.answer:
                self._append_unique(findings, seen, item.pack.answer)

            for claim in item.pack.claims[:3]:
                self._append_unique(findings, seen, claim.claim)

            if not item.pack.answer and not item.pack.claims:
                for page in item.pack.pages[:1]:
                    snippet = self._page_snippet(page)
                    if snippet:
                        self._append_unique(findings, seen, snippet)

        return findings
    
    def _source_urls(self, evidence: list[ResearchEvidence]) -> list[str]:
        urls: list[str] = []
        seen: set[str] = set()

        for item in evidence:
            for claim in item.pack.claims:
                self._append_unique(urls, seen, claim.url)

            for page in item.pack.pages:
                if page.ok:
                    self._append_unique(urls, seen, page.url)

            for result in item.pack.results:
                self._append_unique(urls, seen, result.url)

        return urls 
    
    def _caveats(self, plan: ResearchPlan, evidence: list[ResearchEvidence], source_urls: list[str]) -> list[str]:
        caveats: list[str] = []
        seen: set[str] = set()

        if not source_urls:
            self._append_unique(caveats, seen, "No source evidence was available.")

        if len(source_urls) == 1:
            self._append_unique(caveats, seen, "Only one distinct source was available.")

        for note in plan.ambiguity_notes:
            self._append_unique(caveats, seen, note)

        if plan.freshness_sensitive:
            self._append_unique(caveats, seen, "This query is freshness-sensitive; results may change quickly.")

        text_blob = " ".join(
            [
                plan.original_query,
                *plan.ambiguity_notes,
                *[
                    claim.claim
                    for item in evidence
                    for claim in item.pack.claims
                ],
                *[
                    item.pack.answer or ""
                    for item in evidence
                ],
            ]
        ).casefold()

        if "forecast" in text_blob or "estimate" in text_blob or "projection" in text_blob:
            self._append_unique(caveats, seen, "Some values may be forecasts, estimates, or projections rather than final actuals.")

        for item in evidence:
            for caveat in item.pack.caveats:
                self._append_unique(caveats, seen, caveat)
            if item.pack.provider_errors:
                self._append_unique(caveats, seen, "Some search providers failed.")
            if item.pack.fetch_errors:
                self._append_unique(caveats, seen, "Some pages could not be fetched.")

        if source_urls and not self._has_preferred_or_official_source(source_urls):
            self._append_unique(caveats, seen, "No clearly authoritative source was identified.")

        return caveats
    
    def _confidence(self, source_urls: list[str], caveats: list[str]) -> str:

        if not source_urls or len(source_urls) < 2:
            return "low"
        
        caveat_text = " ".join(caveats).casefold()
        if "no clarity authoritative" in caveat_text:
            return "low"
        
        if len(source_urls)>=3:
            return "high"
        
        return "medium"
    
    def _has_preferred_or_official_source(self, urls: list[str]) -> bool:
        labels = {self.source_policy.source_label(url) for url in urls}
        return bool(labels & {"official", "academic", "financial news", "reputable news", "primary company source"})
    
    def _page_snippet(self, page: FetchedPage) -> str:
        if not page.ok or not page.text.strip():
            return ""
        
        first_sentence = page.text.strip().split(". ", 1)[0].strip()
        if not first_sentence:
            return ""
        if not first_sentence.endswith((".", "!", "?")):
            first_sentence += "."
        return first_sentence
    
    def _append_unique(self, values: list[str], seen: set[str], value: str) -> None:
        normalized = " ".join(value.strip().split())
        if not normalized:
            return
        key = normalized.casefold()
        if key in seen:
            return
        seen.add(key)
        values.append(normalized)

    def _append_url(self, urls: list[str], seen: set[str], url: str) -> None:
        normalized = url.strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        urls.append(normalized)