import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List
from ai_employees.dto import AiEmployeeName, AiEmployeeType
from ai_employees.dto import AiEmployeeTaskConfiguration
from ai_employees.test_data import test_task_data            # <-- REMOVE THIS WHEN WE GET DATA FROM DATABASE


# Called every midnight?
def run_ai_employee_tasks():
    task_data = test_task_data
    for data in task_data:
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.submit(process_ai_employee_configuration, data.get("user_id", None), data.get("data", None))
    pass


def parse_task_configuration(
        task_configuration: dict
) -> List[AiEmployeeTaskConfiguration]:
    configurations = []
    for employee_name, configuration in task_configuration.items():
        configurations.append(
            AiEmployeeTaskConfiguration(
                employee_name, configuration
            )
        )
        # print(f"Configuration till {employee_name} is {configurations}")
    return configurations


def process_ai_employee_configuration(
        user_id: uuid.uuid4,
        task_configuration: dict
) -> None:
    task_information: List[AiEmployeeTaskConfiguration] = parse_task_configuration(task_configuration)
    for task in task_information:
        if task.to_run and task.data_holder:
            print(f'Running {task.agent_name} for {user_id=}...')
            task.data_holder.execute()


if __name__ == '__main__':
    run_ai_employee_tasks()