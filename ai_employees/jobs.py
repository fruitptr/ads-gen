import uuid
import enum
from concurrent.futures import ThreadPoolExecutor

from dto import AiEmployeeTaskConfiguration
from test_data import test_task_data            # <-- REMOVE THIS WHEN WE GET DATA FROM DATABASE


class AiEmployeeTag(enum.Enum):
    marcus = enum.auto()  # Ad Creator
    valentina = enum.auto()  # QA Agent
    avery = enum.auto()  # Copywriter
    cameron = enum.auto()  # Ad Launcher


# Called every midnight?
def run_ai_employee_tasks():
    task_data = test_task_data
    print("Got task data.")
    for data in task_data:
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.submit(process_ai_employee_configuration, data.get("user_id", None), data.get("data", None))
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
    print("Task Information: ", task_information)
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
    print(f"Running ad creator for {task_conf_dto.user_id}...")
    return ''


def run_qa_specialist(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    print(f"Running qa specialist for {task_conf_dto.user_id}...")
    return ''


def run_copywriter(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    print(f"Running copywriter for {task_conf_dto.user_id}...")
    return ''


def run_ad_launcher(
        task_conf_dto: AiEmployeeTaskConfiguration
) -> str:
    print(f"Running ad launcher for {task_conf_dto.user_id}...")
    return ''

if __name__ == '__main__':
    run_ai_employee_tasks()