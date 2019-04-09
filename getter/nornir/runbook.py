#!/usr/bin/env python

"""
Nornir runbook to run arbitrary commands on network devices
"""

import os
import logging
from nornir import InitNornir
from nornir.plugins.tasks.networking import napalm_cli
from nornir.plugins.functions.text import print_result

def run_commands(task):
    """
    This is a task that runs once per host
    """
    cmds_only = [cmd['command'] for cmd in task.host['commands']]
    result = task.run(task=napalm_cli, commands=cmds_only)
    return result

def write_result(result, path='outputs'):
    """
    This is a function which only runs once
    """

    # Equivalent to Ansible "file" module.
    # Ensure output path exists
    if not os.path.exists(path):
        os.mkdir(path)

    # Equivalent to Ansible "copy" module.
    # for each host, for each command, save CLI output
    print('Saving to disk:')
    for hostname, hostdata in result.items():
        print(f'  host: {hostname}')
        for cmd in hostdata.host['commands']:
            c = cmd['command']
            f = cmd['file_suffix']
            print(f'    - command: {c}, file_suffix: {f} ... ', end='')
            with open(f'{path}/{hostname}_{f}.txt', 'w') as handle:
                cli_output = hostdata[0].result[0].result[c]
                handle.write(cli_output)
                print('OK!')

def main():
    """
    Execution begins here
    """

    nr = InitNornir()
    result = nr.run(task=run_commands)
    # CRITICAL 	50
    # ERROR 	40
    # WARNING 	30
    # INFO 	20
    # DEBUG 	10
    print_result(result, severity_level=logging.WARNING)
    write_result(result)

if __name__ == '__main__':
    main()
