from .models import SearchResult


class SearchAgent:
    def __init__(self, provider=None):
        self.provider = provider

    def build_school_queries(self, school_name: str) -> list[str]:
        return [
            f'{school_name} "online" "non-degree" "credit" courses',
            f'{school_name} "visiting student" "online courses"',
            f'{school_name} "guest student" "online" "credit"',
            f'{school_name} "non-matriculated" "online" "credit"',
            f'{school_name} "individual courses" "online" "credit"',
            f'{school_name} "universal learner courses" "credit"',
            f'{school_name} "universal learner" "online" "credit"',
            f'{school_name} "independent study" "university courses" "credit"',
            f'{school_name} "independent study" "tuition" "credit hours"',
            f'{school_name} "undergraduate online courses" "non-degree"',
            f'{school_name} "tuition" "non-degree" "online"',
            f'{school_name} "bursar" "online tuition" "per credit"',
        ]

    def build_price_queries(
        self,
        school_name: str,
        program_name=None,
        course_code=None,
    ) -> list[str]:
        queries = [
            f'{school_name} "online tuition" "per credit"',
            f'{school_name} "non-degree" tuition "per credit"',
            f'{school_name} "visiting student" tuition',
            f'{school_name} "guest student" tuition',
            f'{school_name} "distance education" tuition',
            f'{school_name} "undergraduate tuition" "online"',
            f'{school_name} "bursar" "non-degree"',
        ]

        if program_name:
            queries.extend([
                f'{program_name} cost',
                f'{program_name} tuition',
                f'{program_name} price',
            ])

        if course_code:
            queries.extend([
                f'{school_name} "{course_code}" cost',
                f'{school_name} "{course_code}" tuition',
                f'{school_name} "{course_code}" enroll',
            ])

        return queries

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        if self.provider is None:
            raise RuntimeError("Search provider is not configured.")

        raw_results = await self.provider.search(query, max_results=max_results)

        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", ""),
            )
            for item in raw_results
        ]
