#!/usr/bin/env python

"""
Nornir runbook to run arbitrary commands on network devices
"""

import os
import logging
from nornir import InitNornir
from nornir.plugins.tasks.networking import napalm_cli
from nornir.plugins.tasks.files import write_file
from nornir.plugins.functions.text import print_result

def runcmd_file(task):
    """
    This is a task that runs once per host
    """
    cmds_only = [cmd['command'] for cmd in task.host['commands']]
    result = task.run(task=napalm_cli, commands=cmds_only)
    # ^ this is a MultiResult
    
    for item in task.host['commands']:
        cmd = item['command']
        suf = item['file_suffix']
        task.run(task=write_file, content=result[0].result[cmd],
            filename=f'outputs/{task.host.name}_{suf}.txt')

    return result

def main():
    """
    Execution begins here
    """

    if not os.path.exists('outputs'):
        os.mkdir('outputs')

    nr = InitNornir()
    result = nr.run(task=runcmd_file)

    # CRITICAL 	50
    # ERROR 	40
    # WARNING 	30
    # INFO 	20
    # DEBUG 	10
    print_result(result, severity_level=logging.WARNING)

if __name__ == '__main__':
    main()
