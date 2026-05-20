from .models import CourseFact


class FactMerger:
    def summarize(self, facts: list[CourseFact]) -> dict:
        by_type = {}

        for fact in facts:
            by_type.setdefault(fact.fact_type, []).append(fact)

        best = {}
        for fact_type, items in by_type.items():
            items_sorted = sorted(items, key=lambda x: x.confidence, reverse=True)
            top = items_sorted[0]
            best[fact_type] = {
                "value_text": top.value_text,
                "value_number": top.value_number,
                "value_json": top.value_json,
                "source_url": top.source_url,
                "source_snippet": top.source_snippet,
                "confidence": top.confidence,
            }

        status = self._final_status(best)

        return {
            "status": status,
            "best_facts": best,
            "missing": self.find_missing(best),
        }

    def find_missing(self, best: dict) -> list[str]:
        missing = []

        if "is_online" not in best:
            missing.append("is_online")

        if "is_academic_credit" not in best:
            missing.append("is_academic_credit")

        if "is_non_degree_accessible" not in best:
            missing.append("is_non_degree_accessible")

        if "registration_url" not in best:
            missing.append("registration_url")

        if not any(k in best for k in ["price_per_credit", "price_per_course", "price_candidate"]):
            missing.append("price")

        return missing

    def _final_status(self, best: dict) -> str:
        has_online = best.get("is_online", {}).get("value_text") == "true"
        has_credit = best.get("is_academic_credit", {}).get("value_text") == "true"
        has_non_degree = best.get("is_non_degree_accessible", {}).get("value_text") == "true"
        has_price = any(k in best for k in ["price_per_credit", "price_per_course", "price_candidate"])

        if has_online and has_credit and has_non_degree and has_price:
            return "confirmed_or_likely_available"

        if has_online and has_credit and has_non_degree:
            return "available_price_unknown"

        if has_online and has_credit:
            return "eligibility_unclear"

        return "needs_review"
