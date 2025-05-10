from typing import List, Union
from dataclasses import dataclass

from ai_employees.sub_employees.data import EmployeeDataHolder


@dataclass(frozen=True)
class AveryDataHolder(EmployeeDataHolder):
    tone: str
    length: Union[int, str]
    guidance: str
    ctas: List[str]

    @staticmethod
    def from_dict(configuration: dict):
        return AveryDataHolder(
            tone=configuration.get('tone', ''),
            length=configuration.get('length', 0),
            guidance=configuration.get('guidance', ''),
            ctas=configuration.get('ctas', [])
        )

    def is_run_able(self) -> bool:
        return True

    def execute(self, userid: str):
        pass
