import sys
import subprocess

from cache import cache


class ProcessFab(object):
    def __init__(self, path, task, encoding):
        super(ProcessFab, self).__init__()
        self.path = path
        self.task = task

        self.popen = subprocess.Popen(
                [cache.fab, self.task, '-f', self.path],
                bufsize=1,
                close_fds='posix' in sys.builtin_module_names,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE)

    def read_data(self):
        return self.popen.stdout.read(1)

    def write_data(self, data):
        (bytes, how_many) = self.encoder(data)

        si = self.popen.stdin
        si.write(bytes)
        si.flush()

    def is_alive(self):
        s = self.popen.poll()
        print "is_alive?", s
        return s is None

    def kill(self):
        print "termina processes"
        self.popen.kill()
        self.popen.terminate()
