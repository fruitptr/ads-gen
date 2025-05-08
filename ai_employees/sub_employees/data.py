from abc import ABC, abstractmethod


class EmployeeDataHolder(ABC):

    @staticmethod
    @abstractmethod
    def from_dict(configuration: dict):
        pass

    @abstractmethod
    def is_run_able(self) -> bool:
        pass

    @abstractmethod
    def execute(self) -> None:
        pass