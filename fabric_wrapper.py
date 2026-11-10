# coding: utf-8
import json
import os
import re
import shlex
import subprocess


# Virtualenv folders looked for at the top level of each project folder.
VENV_DIRS = ('.venv', 'venv', 'env', '.env')

if os.name == 'nt':
    VENV_FAB = (os.path.join('Scripts', 'fab.exe'),
                os.path.join('Scripts', 'fab'))
else:
    VENV_FAB = (os.path.join('bin', 'fab'),)


class TaskException(Exception):
    """
    Raised when cant get tasks from fabfile.
    """


def is_runnable(path):
    """
    Return True if `path` looks like an executable that can actually run.

    Besides existing and being executable, a script's shebang interpreter
    must exist: a virtualenv created on another machine (e.g. inside a VM)
    has a `bin/fab` whose interpreter is missing on this one.
    """
    if not os.path.isfile(path):
        return False
    if os.name == 'nt':
        return True
    if not os.access(path, os.X_OK):
        return False
    try:
        with open(path, 'rb') as f:
            first_line = f.readline(512)
    except (IOError, OSError):
        return False
    if first_line.startswith(b'#!'):
        parts = first_line[2:].strip().split()
        if parts:
            interpreter = parts[0].decode('utf-8', 'replace')
            if os.path.isabs(interpreter) and \
                    not os.path.exists(interpreter):
                return False
    return True


def parse_fab_version(output):
    """
    Return Fabric's major version from `fab --version` output, or None.

    Fabric 1 prints "Fabric 1.14.0", the Python 3 fork of Fabric 1 prints
    "Fabric3 1.14.post1", and Fabric 2/3 print "Fabric 3.2.3".
    """
    match = re.match(r'\s*Fabric\d*\s+(\d+)', output)
    return int(match.group(1)) if match else None


def flatten_task_names(collection, prefix=''):
    """
    Return the task names of a `fab --list --list-format json` collection,
    with sub-collection tasks dotted as the CLI expects ("docs.build").
    """
    names = [prefix + task['name'] for task in collection.get('tasks', [])]
    for sub in collection.get('collections', []):
        names.extend(flatten_task_names(sub, prefix + sub['name'] + '.'))
    return names


class FabricWrapper(object):
    """
    Wrapper around some fabric apis.
    """
    def __init__(self):
        self._tasks = {}
        self.folders = []
        self.fab = 'fab'
        self._version = None

    def configure(self, folders, fab_path=None, search_virtualenv=True):
        """
        Set the project folders and choose the `fab` executable to use.
        """
        self.folders = list(folders or [])
        self.fab = self.resolve_fab(fab_path, search_virtualenv)
        self._version = None

    @property
    def version(self):
        """
        Major version of the configured `fab`, detected once per configure().

        Anything that does not report itself as Fabric 1 is treated as
        Fabric 2+, the only Fabric published since 2018.

        Raises OSError if `fab` cannot be run.
        """
        if self._version is None:
            process = subprocess.Popen(
                [self.fab, '--version'],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _ = process.communicate()
            self._version = parse_fab_version(
                stdout.decode('utf-8', 'replace')) or 2
        return self._version

    def list_command(self, fabfile):
        """ Command line that lists the tasks of `fabfile`. """
        if self.version == 1:
            return [self.fab, '--shortlist', '-f', fabfile]
        return self._fabfile_args(fabfile) + ['--list', '--list-format',
                                              'json']

    def run_command(self, fabfile, task, args=''):
        """
        Command line that runs `task` from `fabfile`, with the arguments
        typed by the user in `args`, in the syntax of the Fabric version:

        - Fabric 1: "arg1,key=value", passed as `task:arg1,key=value`.
        - Fabric 2+: "--key=value", "value" or "-k value", split like a
          shell would (quotes group words) and passed after the task.

        Raises ValueError if `args` has unbalanced quotes (Fabric 2+).
        """
        args = (args or '').strip()
        if self.version == 1:
            if args:
                task = '%s:%s' % (task, args)
            return [self.fab, task, '-f', fabfile]
        return self._fabfile_args(fabfile) + [task] + shlex.split(args)

    def arguments_example(self):
        """ Example of the argument syntax, for the input panel caption. """
        if self.version == 1:
            return 'arg1,key=value'
        return '--key=value'

    def _fabfile_args(self, fabfile):
        """
        Fabric 2+ has no -f/--fabfile: the folder to search and the module
        name are given separately (-f now means --config).
        """
        folder, name = os.path.split(fabfile)
        return [self.fab, '--search-root', folder,
                '--collection', os.path.splitext(name)[0]]

    def resolve_fab(self, fab_path=None, search_virtualenv=True):
        """
        Return the `fab` executable to use, in this order:

        1. `fab_path`, if given. A relative path with a directory part
           (".venv/bin/fab") is resolved against the first project folder;
           a bare name ("fab3") is looked up on the PATH.
        2. If `search_virtualenv`, a runnable `fab` inside a virtualenv at
           the top level of a project folder (see VENV_DIRS).
        3. `fab`, looked up on the PATH.
        """
        if fab_path:
            path = os.path.expanduser(fab_path)
            if os.path.dirname(path) and not os.path.isabs(path) \
                    and self.folders:
                path = os.path.join(self.folders[0], path)
            return path

        if search_virtualenv:
            for folder in self.folders:
                for venv in VENV_DIRS:
                    for rel in VENV_FAB:
                        candidate = os.path.join(folder, venv, rel)
                        if is_runnable(candidate):
                            return candidate

        return 'fab'

    @property
    def fabfiles(self):
        fabfiles = []
        for f in self._get('fabfile.py'):
            fabfiles.extend(f)
        return list(filter(None, fabfiles))

    def _get(self, filename):
        """
        Find and return (per folder) `filename` in project folders.

        Uses os.walk instead of the Unix `find` command so it also works
        on Windows, where `find` is an unrelated text-search tool.
        """
        for folder in self.folders:
            found = []
            for root, dirs, files in os.walk(folder):
                if filename in files:
                    found.append(os.path.join(root, filename))
            yield found

    def get_tasks(self, fabfile_name):
        """
        Return tasks list from fabfile.
        Use simple cache by `fab` executable, fabfile abs path & fabfile mtime.

        Raises OSError if the `fab` executable cannot be run.
        """
        key = (self.fab, fabfile_name)
        if self._tasks.get(key):
            time, tasks = self._tasks[key]
            if time >= os.stat(fabfile_name).st_mtime:
                return tasks

        result = subprocess.Popen(
            self.list_command(fabfile_name),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = result.communicate()
        stdout = stdout.decode('utf-8', 'replace')

        # Only the exit code means failure: warnings on stderr (e.g.
        # deprecation warnings from paramiko) must not hide the tasks.
        if result.returncode != 0:
            raise TaskException(
                stderr.decode('utf-8', 'replace').strip() or stdout.strip())

        if self.version == 1:
            ft = [line.strip() for line in stdout.splitlines()
                  if line.strip()]
        else:
            try:
                ft = flatten_task_names(json.loads(stdout))
            except (ValueError, KeyError, TypeError, AttributeError) as e:
                raise TaskException(
                    'Unexpected output from %s --list: %s' % (self.fab, e))

        self._tasks[key] = (os.stat(fabfile_name).st_mtime, ft)

        return ft

fabric_wrapper = FabricWrapper()
