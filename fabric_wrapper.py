# coding: utf-8
import os
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


class FabricWrapper(object):
    """
    Wrapper around some fabric apis.
    """
    def __init__(self):
        self._tasks = {}
        self.folders = []
        self.fab = 'fab'

    def configure(self, folders, fab_path=None, search_virtualenv=True):
        """
        Set the project folders and choose the `fab` executable to use.
        """
        self.folders = list(folders or [])
        self.fab = self.resolve_fab(fab_path, search_virtualenv)

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
            [self.fab, '--shortlist', '-f', fabfile_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = result.communicate()

        if stderr:
            raise TaskException(stderr.decode())

        ft = list(filter(None, stdout.decode().split('\n')))
        self._tasks[key] = (os.stat(fabfile_name).st_mtime, ft)

        return ft

fabric_wrapper = FabricWrapper()
