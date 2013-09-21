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
        try:
            exefab = self._get('fab').next()[0]
            return exefab if exefab != '' else 'fab'
        except StopIteration:
            return 'fab'

    @property
    def fabfiles(self):
        fabfiles = []
        map(fabfiles.extend, self._get('fabfile.py'))
        return filter(None, fabfiles)

    def _get(self, filename):
        """
        Find and return (per folder) `filename` in project folders.
        """
        for folder in self.folders:
            params = ['find', folder, '-name', filename]
            stdout = subprocess.Popen(params,
                                      stdout=subprocess.PIPE).stdout.read()
            found = stdout.split('\n')
            if found:
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
            raise TaskException(stderr)

        ft = filter(None, stdout.split('\n'))
        self._tasks[fabfile_name] = (os.stat(fabfile_name).st_mtime, ft)

        return self._tasks[fabfile_name][1]

fabric_wrapper = FabricWrapper()
