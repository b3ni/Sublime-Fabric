# coding: utf-8
import os
import sys
import subprocess

try:
    from .fabric_wrapper import fabric_wrapper
except ValueError:
    from fabric_wrapper import fabric_wrapper


class ProcessFab(object):
    def __init__(self, path, task, encoding, args=''):
        super(ProcessFab, self).__init__()
        self.path = path
        self.task = task

        query = fabric_wrapper.run_command(self.path, self.task, args)
        # PYTHONUNBUFFERED: fab writes to a pipe here, so without it the
        # output would only show up when the task ends.
        env = dict(os.environ, PYTHONUNBUFFERED='1')
        params = dict(close_fds='posix' in sys.builtin_module_names,
                      stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE, env=env)

        self.popen = subprocess.Popen(query, **params)

    def read_data(self):
        return self.popen.stdout.read(1)

    def is_alive(self):
        s = self.popen.poll()
        return s is None

    def kill(self):
        self.popen.kill()
        self.popen.terminate()
