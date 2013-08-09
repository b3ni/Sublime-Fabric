# coding: utf-8
import sys
import subprocess

from fabric_wrapper import fabric_wrapper


class ProcessFab(object):
    def __init__(self, path, task, encoding):
        super(ProcessFab, self).__init__()
        self.path = path
        self.task = task

        query = [fabric_wrapper.fab, self.task, '-f', self.path]
        params = dict(bufsize=1, close_fds='posix' in sys.builtin_module_names,
                      stderr=subprocess.STDOUT, stdin=subprocess.PIPE,
                      stdout=subprocess.PIPE)

        self.popen = subprocess.Popen(query, **params)

    def read_data(self):
        return self.popen.stdout.read(1)

    def is_alive(self):
        s = self.popen.poll()
        return s is None

    def kill(self):
        self.popen.kill()
        self.popen.terminate()
