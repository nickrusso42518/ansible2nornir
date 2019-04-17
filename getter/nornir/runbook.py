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


def run_cmds_save_output(task: Task, path: str) -> None:
    """
    This is a grouped task that runs once per host. This
    iteration happens inside nornir automatically. Anytime
    'task.run()' is invoked, a new result is automatically added to
    the MultiResult assembled on a per-host basis. If the grouped
    task returns anything, that object is stored in MultiResult[0]
    and all subsequent results are stored thereafter.
    """

    # Pull out only the "command" values to form a list of strings
    cmds_only = [cmd["command"] for cmd in task.host["commands"]]

    # Use the "napalm_cli" connection handler to run all the
    # commands on the device. This returns a MultiResult which
    # contains the NAPALM result in MultiResult[0]
    result = task.run(task=napalm_cli, commands=cmds_only)

    # Manually iterate over each dict in the "commands" list
    for item in task.host["commands"]:

        # Store a few local variables to simplify the Nornir task
        cmd = item["command"]
        suf = item["file_suffix"]

        # Each command output will get written to its own file.
        # This uses the built-in "write_file" operation, using
        # the output gathered by NAPALM as the text to store.
        # The name of the file will be, for example:
        #    outputs/csr_igp.txt
        #    outputs/xrv_ver.txt
        task.run(
            task=write_file,
            content=result[0].result[cmd] + "\n",
            filename=f"{path}/{task.host.name}_{suf}.txt",
        )


def basic_setup(path: str) -> None:
    """
    This is a standard Python function, not a Nornir grouped task.
    Any arbitrary Python code can run here independently from Nornir.
    This function just creates a directory for command outputs.
    """

    if not os.path.exists(path):
        os.mkdir(path)


def main() -> None:
    """
    Execution begins here.
    """

    # Perform initial setup.
    path = "outputs"
    basic_setup(path)

    # Initialize nornir and invoke the grouped task.
    nornir = InitNornir()
    result = nornir.run(task=run_cmds_save_output, path=path)

    # Use Nornir-supplied function to pretty-print the result
    # to see a recap of all actions taken. Standard Python logging
    # levels are supported to set output verbosity.
    print_result(result, severity_level=logging.INFO)


if __name__ == "__main__":
    main()
