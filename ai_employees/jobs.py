import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
from ai_employees.dto import AiEmployeeName, AiEmployeeType
from ai_employees.dto import AiEmployeeTaskConfiguration
from ai_employees.test_data import test_task_data            # <-- REMOVE THIS WHEN WE GET DATA FROM DATABASE
from ai_employees.utils import utils
from dotenv import load_dotenv

load_dotenv()


EXECUTION_ORDER = ["Marcus", "Valentina", "Avery", "Cameron"]
DEPENDENCIES = {
    "Valentina": ["Marcus"],
    "Avery": ["Cameron"],
    "Cameron": ["Avery"]
}

# Called every midnight?
def run_ai_employee_tasks():
    connection = utils.connect_to_database()
    if connection:
        utils.ensure_table_exists(connection)
    task_data = test_task_data
    for data in task_data:
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.submit(process_ai_employee_configuration, data.get("user_id", None), data.get("data", None), connection)
    utils.close_connection(connection) 


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
    return configurations


def validate_dependencies(
        task_configs: List[AiEmployeeTaskConfiguration]
) -> List[AiEmployeeTaskConfiguration]:
    """
    Validates dependencies between AI employees and returns a filtered and sorted list 
    based on the dependency rules and execution order.
    
    Rules:
    1. Valentina can only exist if Marcus exists
    2. Avery and Cameron have mutual dependency - both exist or neither exists
    3. Execution order: Marcus -> Valentina -> Avery -> Cameron
    """

    config_map = {config.agent_name: config for config in task_configs if config.to_run}

    invalid_employees = set()

    if "Valentina" in config_map and "Marcus" not in config_map:
        invalid_employees.add("Valentina")

    if ("Avery" in config_map and "Cameron" not in config_map) or \
       ("Cameron" in config_map and "Avery" not in config_map):
        invalid_employees.add("Avery")
        invalid_employees.add("Cameron")

    valid_configs = [config for config in task_configs 
                     if config.agent_name not in invalid_employees and config.to_run]

    return sorted(valid_configs, 
                  key=lambda config: EXECUTION_ORDER.index(config.agent_name) 
                  if config.agent_name in EXECUTION_ORDER else float('inf'))


def process_ai_employee_configuration(
        user_id: uuid.uuid4,
        task_configuration: dict,
        connection
) -> None:
    task_information: List[AiEmployeeTaskConfiguration] = parse_task_configuration(task_configuration)

    valid_tasks = validate_dependencies(task_information)
    
    print(f"Running {len(valid_tasks)} valid tasks for user {user_id}")

    for task in valid_tasks:
        if task.data_holder:
            print(f'Running {task.agent_name} for {user_id=}...')
            task.data_holder.execute(user_id, connection)


if __name__ == '__main__':
    run_ai_employee_tasks()