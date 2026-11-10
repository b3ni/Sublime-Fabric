# coding: utf-8
import os
import subprocess


class TaskException(Exception):
    """
    Raised when cant get tasks from fabfile.
    """


class FabricWrapper(object):
    """
    Wrapper around some fabric apis.
    """
    def __init__(self):
        self._tasks = {}
        self.folders = []

    def set_folders(self, folders):
        self.folders = folders

    @property
    def fab(self):
        # Igual que antes: solo se mira la primera carpeta del proyecto.
        for found in self._get('fab'):
            return found[0] if found else 'fab'
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
        Use simple cache by fabfile abs path & fabfile mtime.
        """
        if self._tasks.get(fabfile_name):
            time, tasks = self._tasks[fabfile_name]
            if time >= os.stat(fabfile_name).st_mtime:
                return tasks

        result = subprocess.Popen(
            [self.fab, '--shortlist', '-f', fabfile_name],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        stdout, stderr = result.stdout.read(), result.stderr.read()

        if stderr:
            raise TaskException(stderr.decode())

        ft = list(filter(None, stdout.decode().split('\n')))
        self._tasks[fabfile_name] = (os.stat(fabfile_name).st_mtime, ft)

        return self._tasks[fabfile_name][1]

fabric_wrapper = FabricWrapper()
