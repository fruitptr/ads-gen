import uuid
import enum

from ai_employees.dto import AiEmployeeTaskConfiguration


class AiEmployeeTag(enum.Enum):
    marcus = enum.auto()  # Ad Creator
    valentina = enum.auto()  # QA Agent
    avery = enum.auto()  # Copywriter
    cameron = enum.auto()  # Ad Launcher


# Called every midnight?
def run_ai_employee_tasks():
    # We pull all the task configs here and pass it down to an individual job to process what needs to
    # be done. (AD Creator, QA Specialist, Copywriter and Ad Launcher)
    #
    for data in task_data:
        # run in executor loop
        process_ai_employee_configuration(data.user_id, data.data)
    pass


def parse_task_configuration(
        task_configuration: dict
) -> AiEmployeeTaskConfiguration:
    pass


def process_ai_employee_configuration(
        user_id: uuid.uuid4,
        task_configuration: dict
) -> None:
    task_information = parse_task_configuration(task_configuration)
    for task in task_information:
        if task.to_run:
            if task.AgentType == AiEmployeeTag.marcus:
                pass



def run_task1(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''

def run_task2(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''

def run_task3(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''

def run_task4(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''
