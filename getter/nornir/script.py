from nornir import InitNornir
from nornir.plugins.tasks.networking import napalm_cli
from nornir.plugins.functions.text import print_result

def run_commands(task):
    cmds_only = [cmd['command'] for cmd in task.host['commands']]
    result = task.run(task=napalm_cli, commands=cmds_only)
    return result

def write_result(result):
    # very broken, need diff files for outputs along the way
    with open('test.txt', 'w') as handle:
        for hostname,hostdata in result.items():
            handle.write(f'host: {hostname}')
            for cmd in hostdata.host['commands']:
                handle.write(hostdata[0].result[0].result[cmd['command']])
    

def main():
    nr = InitNornir()
    result = nr.run(task=run_commands)
    print_result(result)
    write_result(result)

if __name__ == '__main__':
    main()
