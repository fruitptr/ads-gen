import enum

from ai_employees.sub_employees.marcus.data import MarcusDataHolder
from ai_employees.sub_employees.valentina.data import ValentinaDataHolder


class AiEmployeeName(enum.Enum):
    marcus = enum.auto()  # Ad Creator
    valentina = enum.auto()  # QA Agent
    avery = enum.auto()  # Copywriter
    cameron = enum.auto()  # Ad Launcher
    unknown = enum.auto()  # fallback

    @staticmethod
    def __from_name__(name):
        if isinstance(name, AiEmployeeName):
            return name
        if name is not None:
            for status in AiEmployeeName:
                if status.name == name:
                    return status
        return AiEmployeeName.unknown


class AiEmployeeType(enum.Enum):
    ADS = enum.auto()
    QA = enum.auto()
    COPYWRITER = enum.auto()
    AD_LAUNCHER = enum.auto()
    UNKNOWN = enum.auto()

    @staticmethod
    def __from_name__(name):
        if isinstance(name, AiEmployeeType):
            return name
        if name is not None:
            for status in AiEmployeeType:
                if status.name == name:
                    return status
        return AiEmployeeType.UNKNOWN


agent_name_to_agent_type_dict = {
    AiEmployeeName.marcus: AiEmployeeType.ADS,
    AiEmployeeName.valentina: AiEmployeeType.QA,
    AiEmployeeName.avery: AiEmployeeType.COPYWRITER,
    AiEmployeeName.cameron: AiEmployeeType.AD_LAUNCHER,
    AiEmployeeName.unknown: AiEmployeeType.UNKNOWN
}

agent_type_to_data_holder = {
    AiEmployeeType.ADS: MarcusDataHolder,
    AiEmployeeType.QA: ValentinaDataHolder
}


class AiEmployeeTaskConfiguration:
    def __init__(self, agent_name: str, configuration: dict):
        self.agent_name = agent_name
        self.configuration = configuration
        self.agent_type: AiEmployeeType = agent_name_to_agent_type_dict.get(AiEmployeeName.__from_name__(self.agent_name))
        self.data_holder = agent_type_to_data_holder.get(self.agent_type, None)
        if self.data_holder:
            self.data_holder = self.data_holder.from_dict(self.configuration)
        self.to_run: bool = self.is_job_to_run()

    def is_job_to_run(self) -> bool:
        if self.data_holder:
            return self.data_holder.is_run_able()
        return False

# (AgentType -> QA/AdsGent
#  TO_RUN -> Should we run it or not ?
#  task_def ->
#  )

