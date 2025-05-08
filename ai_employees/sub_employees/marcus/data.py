from typing import List
from dataclasses import dataclass
from datetime import datetime as dt
from zoneinfo import ZoneInfo

from ai_employees.sub_employees.data import EmployeeDataHolder

day_abbr_to_iso = {
    "Mon": 1,
    "Tue": 2,
    "Wed": 3,
    "Thu": 4,
    "Fri": 5,
    "Sat": 6,
    "Sun": 7
}


@dataclass(frozen=True)
class MarcusDataHolder(EmployeeDataHolder):
    ads_per_day: int
    ad_guidance: str
    run_days: List[str]

    @staticmethod
    def from_dict(configuration: dict):
        return MarcusDataHolder(
            ads_per_day=configuration.get('adsPerDay', 0),
            ad_guidance=configuration.get('adGuidance', ''),
            run_days=configuration.get('days')
        )

    def is_run_able(self) -> bool:
        current_day = dt.now(tz=ZoneInfo('UTC')).isoweekday()
        for day in self.run_days:
            if current_day == day_abbr_to_iso.get(day, 1):
                return True
        return False

    def execute(self):
        pass
