======================
Information collection
======================
This tutorial describes how a simple Ansible information collector
compares to the equivalent code in Python using Nornir. Both projects
are heavily documented and this file provides additional comparative context.

----------------
Variable Loading
----------------
Ansible and Nornir both support the concept of automatically loaded inventory
variables. In Ansible, this is the most common way to pass data into a playbook.
It is also common in Nornir, but being pure Python, other options are available,
such as direct CLI arguments or file paths for manual parsing.

The variable loading is hierarchical in both cases, with more specific
(less default-y) definitions taking precedence. In Ansible, the ``all``
group encompasses everything, then the ``devices`` group is a child
group containing the network devices. within that, ``ios`` and ``iosxr``
groups are defined based on network OS::

    # inv.yml
    all:
      children:
        devices:
          children:
            ios:
              hosts:
                CSR:
            iosxr:
              hosts:
                XRV:

Some data is universal, such as login credentials, and so can be applied to
the ``all`` or ``devices`` group::

    # group_vars/all.yml
    ansible_user: admin
    ansible_password: password123
    
Some data is group-specific, such as the exact commands to run on each
device. Different files represent different group data::

    # group_vars/ios.yml
    ansible_network_os: ios
    commands:
      - command: "show ip ospf neighbor"
        file_suffix: "igp"
      - command: "show version"
        file_suffix: "ver"
    
    # group_vars/iosxr.yml
    ansible_network_os: iosxr
    commands:
      - command: "show ospf neighbor"
        file_suffix: "igp"
      - command: "show version"
        file_suffix: "ver"

Nornir can use the exact Ansible inventory structure as well, which is the
easiest migration mechanism. In this example, I show using the "simple"
Nornir inventory, which is formatted differently. The ``hosts.yaml`` file
identifies dictionaries where the key is the hostname and the subkeys
are individual data fields, such as the IP or hostname for connectivity
and group membership::

    # hosts.yaml
    CSR:
      hostname: CSR
      groups:
        - ios

    XRV:
      hostname: XRV
      groups:
        - iosxr

The group structure in Nornir is contained in a single file named
``groups.yaml``. The logic is similar ot the individual Ansible
``group_vars/`` files. At the ``devices`` level, define the common
login credentials. At the network OS level, specific the OS and
parent groups. Both IOS and IOS-XR are subgroups from ``devices``
so be sure to include it to inherit the login credentials. The
``data`` key is special in Nornir and represents the user data
to be automatically loaded and available within Nornir tasks::

    # groups.yaml
    devices:
      username: admin
      password: password123

    ios:
      platform: ios
      groups:
        - devices
      data:
        commands:
          - command: "show ip ospf neighbor"
            file_suffix: "igp"
          - command: "show version"
            file_suffix: "ver"

    iosxr:
      platform: iosxr
      groups:
        - devices
      data:
        commands:
          - command: "show ospf neighbor"
            file_suffix: "igp"
          - command: "show version"
            file_suffix: "ver"

-----------
Basic Setup
-----------
Both projects store their text file outputs in a dynamically-created directory
named ``outputs/``. The operation is idempotent.

In Ansible, the ``block`` construct scopes both the declaration of the ``path``
variable and the creation of the directory. This allows both tasks to be run
on the control machine without using ``network_cli``. Because everything in
Ansible automatically runs on every host in the ``hosts`` key` at the play
level, we must manually instructure Ansible to only run it once::

    - name: "PLAY 1: Collect information from devices"
      hosts: devices
      tasks:
        - name: "BLOCK: Perform one-time setup on control machine"
          block:
            - name: "TASK 1: Identify output directory"
              set_fact:
                outputs: "{{ playbook_dir }}/outputs"
    
            - name: "TASK 2: Create folder for collected output"
              file:
                path: "{{ outputs }}"
                state: directory
          run_once: true
          delegate_to: localhost

Unlike Ansible, Nornir is not host-centric. This is advantageous in
some cases, such as needing to perform an action once. Simply write
the appropriate Python code **outside** of the Nornir task execution
structure. I chose to use a basic Python function ``basic_setup``
to keep the ``main`` function cleaner, but that was not required::

    def basic_setup(path: str) -> None:
        if not os.path.exists(path):
            os.mkdir(path)

    def main() -> None:
        path = "outputs"
        basic_setup(path)

--------------------------
Getting and Storing Output
--------------------------
Next, both solutions need to log into the network devices, run the
required CLI commands, and collect the output. In Ansible, I opted
to use an explicit ``loop`` mechanism to step over each dictionary
in the ``commands`` list, feeding the value from the ``command`` key
into the ``cli_command`` module. I'm storing the results in a dictionary
named ``result`` which contains the results of each command::

    - name: "TASK 3: Run CLI commands"
      cli_command:
        command: "{{ item.command }}"
      register: result
      loop: "{{ commands }}"

Following the data collection, the ``copy`` module is used to store the
output from each command into its own file, again using a separate loop.
Again, note the ``delegate_to`` as this is a control machine action::

    - name: "TASK 4: Write command output to text file"
      copy:
        content: "{{ item.0.stdout }}\n"
        dest: "{{ outputs }}/{{ inventory_hostname }}_{{ item.1.file_suffix }}.txt"
        mode: 0444
      loop: "{{ result.results | zip(commands) | list }}"
      loop_control:
        label: "{{ item.1 }}"
      delegate_to: localhost

The high-level logic in Python pseudo-code of these tasks is::

    for item in commands:
        result += cli_command(item.command)
    for item in zip(results, commands):
        copy(content=item[0].output,dest=item[1].file_suffix) 

Few programmers I know would write this code this way. Putting multiple tasks
inside of a single loop is challenging in Ansible and requires multiple files.
The current implementation means that all hosts must finish their command
collection before any hosts can begin writing to disk. Ansible strategies, such
as ``strategy: free``, can help overcome this.

In Nornir, each grouped task runs completely independently as a separate
thread, which is conceptually like the following code, though not precisely::

    for item in zip(results, commands):
        result += cli_command(item[1].command)
        copy(content=item[0].output,dest=item[1].file_suffix) 

This "function" is called a "grouped task" as Nornir can run any arbitrary
Python function as a task. Inside the grouped task, operators can run
multiple tasks, which again run inside of a thread and don't need to wait
for other hosts to catch up::

    def run_cmds_save_output(task: Task, path: str) -> None:
        cmds_only = [cmd["command"] for cmd in task.host["commands"]]
        result = task.run(task=napalm_cli, commands=cmds_only)

        for item in task.host["commands"]:
            cmd = item["command"]
            suf = item["file_suffix"]
            task.run(
                task=write_file,
                content=result[0].result[cmd] + "\n",
                filename=f"{path}/{task.host.name}_{suf}.txt",
            )

Calling the grouped task is easy. Initialize Nornir first then use ``run``
and pass in the function name to the ``task`` keyword argument. You
can add other arbitrary arguments too, such as ``path`` in this case::

    def main() -> None:
        nornir = InitNornir()
        result = nornir.run(task=run_cmds_save_output, path=path)

----------------------
How Results are Stored
----------------------
TODO, show the Ansible JSON and Nornir object structure, compare them

--------------------
Inspecting the Files
--------------------
These solutions were developed to operate similarly by following a
similar workflow with similar variable names and generating
identical outputs. The file sizes below provide a fair degree
of certainty to prove that the output files are the same, notwithstanding
minor timestamp differences in device uptime and the like::

    (nornir2) [centos@devbox getter]$ ls -l ansible/outputs/*
    -r--r--r-- 1 centos centos  151 Apr 17 15:47 ansible/outputs/CSR_igp.txt
    -r--r--r-- 1 centos centos 2379 Apr 17 15:47 ansible/outputs/CSR_ver.txt
    -r--r--r-- 1 centos centos  306 Apr 17 15:47 ansible/outputs/XRV_igp.txt
    -r--r--r-- 1 centos centos  401 Apr 17 15:47 ansible/outputs/XRV_ver.txt

    (nornir2) [centos@devbox getter]$ ls -l nornir/outputs/*
    -rw-rw-r-- 1 centos centos  151 Apr 17 15:52 nornir/outputs/CSR_igp.txt
    -rw-rw-r-- 1 centos centos 2379 Apr 17 15:52 nornir/outputs/CSR_ver.txt
    -rw-rw-r-- 1 centos centos  306 Apr 17 15:52 nornir/outputs/XRV_igp.txt
    -rw-rw-r-- 1 centos centos  401 Apr 17 15:52 nornir/outputs/XRV_ver.txt
