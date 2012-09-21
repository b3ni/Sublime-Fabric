# Fabric.py
# Sublime-Fabric excute task Fabric for Sublime Text 2
#
# Project: https://github.com/b3ni/Sublime-Fabric
# License: MIT
from itertools import ifilter, chain, imap
import sublime
import sublime_plugin
import subprocess
import os


class FabTasks(sublime_plugin.WindowCommand):
    """Fabric using repl in st2"""
    _fabfiles = []
    def run(self):
        if not self._fabfiles:
            self._fabfiles = chain(*imap(
                lambda folder: ifilter(
                    len, subprocess.Popen(
                        ['find', folder, '-name', 'fabfile.py'],
                    stdout=subprocess.PIPE).stdout.read().split('\n')
                ), self.window.folders(),
            ))
        self.files, self.tasks = zip(*chain(*imap(
            lambda _file: imap(
                lambda task: (_file, task), ifilter(
                    len, subprocess.Popen([
                        'fab', '-l', '-F', 'short', '-f', _file,
                    ], stdout=subprocess.PIPE).stdout.read().split('\n'),
                ),
            ), self._fabfiles,
        )))
        self.window.show_quick_panel(
            list(self.tasks), self.execute,
            sublime.MONOSPACE_FONT,
        )

    def execute(self, index):
        if index != -1:
            task = self.tasks[index]
            path = self.files[index]
            self.window.run_command("repl_open", {
                "type": "subprocess",
                "encoding": "utf8",
                "suppress_echo": True,
                "cmd": ['fab', task, '-f', path],
                'cwd': os.path.dirname(path),
            })
