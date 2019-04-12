#!/usr/bin/env python

"""
Nornir runbook to run arbitrary commands on network devices
"""

import os
import logging
from nornir import InitNornir
from nornir.core.task import Task
from nornir.plugins.tasks.networking import napalm_cli
from nornir.plugins.tasks.files import write_file
from nornir.plugins.functions.text import print_result


def run_cmds_save_output(task: Task) -> None:
    """
    This is a task that runs once per host
    """
    cmds_only = [cmd["command"] for cmd in task.host["commands"]]
    result = task.run(task=napalm_cli, commands=cmds_only)
    # ^ this is a MultiResult

    for item in task.host["commands"]:
        cmd = item["command"]
        suf = item["file_suffix"]
        task.run(
            task=write_file,
            content=result[0].result[cmd],
            filename=f"outputs/{task.host.name}_{suf}.txt",
        )


def basic_setup(output_path: str = "outputs") -> None:
    """
    This is a function disconnected from Nornir operation
    """

    if not os.path.exists(output_path):
        os.mkdir(output_path)


def main() -> None:
    """
    Execution begins here
    """

    basic_setup()
    nornir = InitNornir()
    result = nornir.run(task=run_cmds_save_output)

    # CRITICAL 	50
    # ERROR 	40
    # WARNING 	30
    # INFO 	20
    # DEBUG 	10
    print_result(result, severity_level=logging.INFO)
    # import pdb; pdb.set_trace()


if __name__ == "__main__":
    main()
