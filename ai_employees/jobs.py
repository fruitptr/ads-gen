import uuid
import enum
from concurrent.futures import ThreadPoolExecutor

from ai_employees.dto import AiEmployeeTaskConfiguration
from ai_employees.test_data import test_task_data            # <-- REMOVE THIS WHEN WE GET DATA FROM DATABASE


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
    task_data = test_task_data
    for data in task_data:
        # run in executor loop
        with ThreadPoolExecutor(max_workers=10) as executor:
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
                run_ad_creator(task)
            elif task.AgentType == AiEmployeeTag.valentina:
                run_qa_specialist(task)
            elif task.AgentType == AiEmployeeTag.avery:
                run_copywriter(task)
            elif task.AgentType == AiEmployeeTag.cameron:
                run_ad_launcher(task)
            else:
                raise ValueError(f'Unknown AiEmployeeTag: {task.AgentType}')
    pass


def run_ad_creator(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''


def run_qa_specialist(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''


def run_copywriter(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''


def run_ad_launcher(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    return ''
