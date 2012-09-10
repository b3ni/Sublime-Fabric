# Fabric.py
# Sublime-Fabric excute task Fabric for Sublime Text 2
#
# Project: https://github.com/b3ni/Sublime-Fabric
# License: MIT

import sublime
import sublime_plugin
import os
import subprocess
import threading
import functools


def main_thread(callback, *args, **kwargs):
    # sublime.set_timeout gets used to send things onto the main thread
    # most sublime.[something] calls need to be on the main thread
    sublime.set_timeout(functools.partial(callback, *args, **kwargs), 0)


def do_when(conditional, callback, *args, **kwargs):
    if conditional():
        return callback(*args, **kwargs)
    sublime.set_timeout(functools.partial(do_when, conditional, callback, *args, **kwargs), 50)


def _make_text_safeish(text, fallback_encoding, method='decode'):
    # The unicode decode here is because sublime converts to unicode inside
    # insert in such a way that unknown characters will cause errors, which is
    # distinctly non-ideal...
    try:
        unitext = getattr(text, method)('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        unitext = getattr(text, method)(fallback_encoding)
    return unitext


class CommandThread(threading.Thread):
    def __init__(self, command, on_done, working_dir="", fallback_encoding="", **kwargs):
        threading.Thread.__init__(self)
        self.command = command
        self.on_done = on_done
        self.working_dir = working_dir
        if "stdin" in kwargs:
            self.stdin = kwargs["stdin"]
        else:
            self.stdin = None
        if "stdout" in kwargs:
            self.stdout = kwargs["stdout"]
        else:
            self.stdout = subprocess.PIPE
        self.fallback_encoding = fallback_encoding
        self.kwargs = kwargs

    def run(self):
        try:
            # Per http://bugs.python.org/issue8557 shell=True is required to
            # get $PATH on Windows. Yay portable code.
            shell = os.name == 'nt'
            if self.working_dir != "":
                os.chdir(self.working_dir)

            proc = subprocess.Popen(self.command,
                stdout=self.stdout, stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                shell=shell, universal_newlines=True)
            output = proc.communicate(self.stdin)[0]
            if not output:
                output = ''
            # if sublime's python gets bumped to 2.7 we can just do:
            # output = subprocess.check_output(self.command)
            main_thread(self.on_done, _make_text_safeish(output, self.fallback_encoding), **self.kwargs)
        except subprocess.CalledProcessError, e:
            main_thread(self.on_done, e.returncode)
        except OSError, e:
            if e.errno == 2:
                main_thread(sublime.error_message, "binary could not be found in PATH\n\nPATH is: %s" % os.environ['PATH'])
            else:
                raise e


class Command(object):
    may_change_files = False

    def run_command(self, command, callback=None, show_status=True,
            filter_empty_args=True, no_save=False, **kwargs):
        if filter_empty_args:
            command = [arg for arg in command if arg]
        if 'working_dir' not in kwargs:
            kwargs['working_dir'] = self.get_working_dir()
        if 'fallback_encoding' not in kwargs and self.active_view() and self.active_view().settings().get('fallback_encoding'):
            kwargs['fallback_encoding'] = self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

        if not callback:
            callback = self.generic_done

        thread = CommandThread(command, callback, **kwargs)
        thread.start()

        if show_status:
            message = kwargs.get('status_message', False) or ' '.join(command)
            sublime.status_message(message)

    def generic_done(self, result):
        if self.may_change_files and self.active_view() and self.active_view().file_name():
            if self.active_view().is_dirty():
                result = "WARNING: Current view is dirty.\n\n"
            else:
                # just asking the current file to be re-opened doesn't do anything
                print "reverting"
                position = self.active_view().viewport_position()
                self.active_view().run_command('revert')
                do_when(lambda: not self.active_view().is_loading(), lambda: self.active_view().set_viewport_position(position, False))
                # self.active_view().show(position)

        if not result.strip():
            return

        self.panel(result)

    def _output_to_view(self, output_file, output, clear=False,
            syntax="Packages/Diff/Diff.tmLanguage", **kwargs):
        output_file.set_syntax_file(syntax)
        edit = output_file.begin_edit()
        if clear:
            region = sublime.Region(0, self.output_view.size())
            output_file.erase(edit, region)
        output_file.insert(edit, 0, output)
        output_file.end_edit(edit)

    def scratch(self, output, title=False, position=None, **kwargs):
        scratch_file = self.get_window().new_file()
        if title:
            scratch_file.set_name(title)
        scratch_file.set_scratch(True)
        self._output_to_view(scratch_file, output, **kwargs)
        scratch_file.set_read_only(True)
        if position:
            sublime.set_timeout(lambda: scratch_file.set_viewport_position(position), 0)
        return scratch_file

    def panel(self, output, **kwargs):
        if not hasattr(self, 'output_view'):
            self.output_view = self.get_window().get_output_panel("fabric")
        self.output_view.set_read_only(False)
        self._output_to_view(self.output_view, output, clear=True, **kwargs)
        self.output_view.set_read_only(True)
        self.get_window().run_command("show_panel", {"panel": "output.fabric"})

    def quick_panel(self, *args, **kwargs):
        self.get_window().show_quick_panel(*args, **kwargs)


class WindowCommand(Command, sublime_plugin.WindowCommand):
    def active_view(self):
        return self.window.active_view()

    def _active_file_name(self):
        view = self.active_view()
        if view and view.file_name() and len(view.file_name()) > 0:
            return view.file_name()

    @property
    def fallback_encoding(self):
        if self.active_view() and self.active_view().settings().get('fallback_encoding'):
            return self.active_view().settings().get('fallback_encoding').rpartition('(')[2].rpartition(')')[0]

    def is_enabled(self):
        return True

    def get_file_name(self):
        return ''

    def get_working_dir(self):
        file_name = self._active_file_name()
        if file_name:
            return os.path.realpath(os.path.dirname(file_name))
        else:
            try:  # handle case with no open folder
                return self.window.folders()[0]
            except IndexError:
                return ''

    def get_window(self):
        return self.window


class FabricListTaskCommand(WindowCommand):
    def run(self):
        print "wor", self.get_working_dir()
        self.run_command(['fab', '-l', '-F', 'short'], self.list_task_done, working_dir=self.get_working_dir())

    def list_task_done(self, result):
        self.results = filter(self._status_filter, result.rstrip().split('\n'))

        index_fail = self._index_containing_substring(self.results, u"Fatal error")
        if index_fail != -1:
            sublime.error_message(self.results[index_fail])
            return

        if len(self.results):
            self.show_status_list()
        else:
            sublime.status_message("Nothing to do")

    def show_status_list(self):
        self.quick_panel(self.results, self.panel_done, sublime.MONOSPACE_FONT)

    def panel_done(self, picked):
        if 0 > picked < len(self.results):
            return
        picked_task = self.results[picked]
        self.run_command(['fab', picked_task], self.task_done)

    def task_done(self, result):
        if not result.strip():
            return

        self.scratch(result, title="Task Status")

    def _status_filter(self, item):
        return len(item) > 0

    def _index_containing_substring(self, the_list, substring):
        for i, s in enumerate(the_list):
            if substring in s:
                return i
        return -1
