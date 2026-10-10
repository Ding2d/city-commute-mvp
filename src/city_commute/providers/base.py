from typing import Protocol

from city_commute.models import Candidate, City


class DataProvider(Protocol):
    def candidates(self, city_name: str) -> tuple[City, list[Candidate]]: ...
