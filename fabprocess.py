# coding: utf-8
import os
import sys
import subprocess


class ProcessFab(object):
    """
    Runs a `fab` command line and gives access to its output.

    The command is built by the caller (FabricWrapper.run_command) instead
    of here: Sublime Text loads every top-level .py of the package as a
    plugin and reloads them one by one, so a `fabric_wrapper` imported in
    this module ends up being a different, never configured instance.
    """
    def __init__(self, command, encoding):
        super(ProcessFab, self).__init__()
        self.command = command

        query = command
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
