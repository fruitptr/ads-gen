from typing import Dict, Any
from dataclasses import dataclass

from ai_employees.sub_employees.data import EmployeeDataHolder


@dataclass(frozen=True)
class ValentinaDataHolder(EmployeeDataHolder):
    custom: str
    spell: bool
    grammar: bool
    visuals: bool
    claims: bool
    copyright: bool
    policy: bool
    offensive: bool
    layout: bool
    faces: bool
    cta: bool
    multi_lang: bool
    prompt: bool
    over_promise: bool

    @staticmethod
    def from_dict(configuration: Dict[str, Any]):
        return ValentinaDataHolder(
            custom=configuration.get('custom', ''),
            spell=configuration.get('spell', False),
            grammar=configuration.get('grammar', False),
            visuals=configuration.get('visuals', False),
            claims=configuration.get('claims', False),
            copyright=configuration.get('copyright', False),
            policy=configuration.get('policy', False),
            offensive=configuration.get('offensive', False),
            layout=configuration.get('layout', False),
            faces=configuration.get('faces', False),
            cta=configuration.get('cta', False),
            multi_lang=configuration.get('multiLang', False),
            prompt=configuration.get('prompt', False),
            over_promise=configuration.get('overpromise', False)
        )

    def is_run_able(self) -> bool:
        return True

    def execute(self, userid, connection):
        pass
