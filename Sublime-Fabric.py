# coding: utf-8
import os
import sublime
import sublime_plugin
import threading
try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty
from codecs import getincrementaldecoder
try:
    from . import fabprocess
    from .fabric_wrapper import fabric_wrapper, TaskException
except ValueError:
    import fabprocess
    from fabric_wrapper import fabric_wrapper, TaskException


SETTINGS_FILE = 'Fabric.sublime-settings'

FAB_NOT_FOUND = (
    'Fabric: could not run "%s"\n\n%s\n\n'
    'Set "fab_path" with the command "Preferences: Fabric Settings", '
    'or "fabric_fab_path" in your .sublime-project settings.')


def get_setting(window, key, default=None):
    """
    Read `key` from the project settings ("fabric_<key>" in the "settings"
    section of the .sublime-project file), falling back to
    Fabric.sublime-settings.
    """
    project_key = 'fabric_' + key
    view = window.active_view()
    if view is not None:
        value = view.settings().get(project_key)
        if value is not None:
            return value
    if hasattr(window, 'project_data'):
        data = window.project_data() or {}
        value = data.get('settings', {}).get(project_key)
        if value is not None:
            return value
    return sublime.load_settings(SETTINGS_FILE).get(key, default)


def enqueue_output(process, queue):
    while True:
        # print "voy a read"
        bs = process.read_data()
        # print "read", bs
        if bs:
            queue.put(bs)
        else:
            break


def read_output(queue, encoding):
    decoder = getincrementaldecoder(encoding)()
    data = ""
    try:
        while True:
            packet = queue.get_nowait()
            if packet is None:
                try:
                    output = decoder.decode(data)
                except Exception:
                    output = "[Fabric: decode error]\n"
                return output, False
            data += decoder.decode(packet)
    except Empty:
        try:
            output = data
        except Exception:
            output = "[Fabric: decode error]\n"
        return output, True


class TaskFabric(object):
    def __init__(self, window, encoding, path, task, args=''):
        super(TaskFabric, self).__init__()
        self.window = window
        self.encoding = encoding

        # ejecutamos proceso antes de crear la vista, para no dejar una
        # vista vacía si `fab` no se puede ejecutar (OSError)
        self.fab = fabprocess.ProcessFab(
            fabric_wrapper.run_command(path, task, args), encoding)

        self.view = self.window.new_file()
        self.view.settings().set("translate_tabs_to_spaces", False)
        self.view.settings().set("auto_indent", False)
        self.view.settings().set("smart_indent", False)
        self.view.settings().set("indent_subsequent_lines", False)
        self.view.settings().set("detect_indentation", False)
        self.view.settings().set("auto_complete", False)
        self.view.set_scratch(True)
        self.view.set_read_only(True)
        self.view.set_name("[FABRIC] [%s]" % " ".join(
            filter(None, [task, (args or '').strip()])))

        # ejecutamos hebra de lectura
        self.q = Queue()
        self.t = threading.Thread(target=enqueue_output,
                                  args=(self.fab, self.q))
        self.t.daemon = True
        self.t.start()

        self._output_end = 0
        self._kill = False

        self.update_view_loop()

    @property
    def input_region(self):
        return sublime.Region(self._output_end, self.view.size())

    def new_output(self):
        data, is_still_working = read_output(self.q, self.encoding)
        return data, is_still_working

    def update_view_loop(self):
        """ Loop que actualiza el buffer de sublime """
        (data, is_still_working) = self.new_output()

        if data:
            # escribimos en el buffer
            v = self.view
            v.set_read_only(False)
            # añadimos al final del buffer, no en la posición 0
            v.run_command('task_view',
                          {'data': data, 'output_end': v.size()})
            self._output_end = v.size()
            v.set_read_only(True)
            v.show(self.input_region)

        if is_still_working and not self._kill:
            sublime.set_timeout(self.update_view_loop, 1000)

    def close(self):
        # si el proceso sigue vivo lo matamos
        if self.fab.is_alive():
            self.fab.kill()
        self._kill = True


class TaskViewCommand(sublime_plugin.TextCommand):

    def run(self, edit, data, output_end):
        try:
            self.view.insert(edit, output_end, data)
        finally:
            self.view.end_edit(edit)
            self.view.set_read_only(True)


class TaskManager(object):
    def __init__(self):
        self._task = {}

    def run_task(self, window, encoding, path, task_name, args=''):
        t = TaskFabric(window, encoding, path, task_name, args)
        self._task[t.view.id()] = t

    def close(self, view):
        if view.id() in self._task:
            t = self._task[view.id()]
            t.close()
            del self._task[view.id()]


manager = TaskManager()

# Last arguments typed for each (fabfile, task), to prefill the input panel.
last_arguments = {}


class FabTasksCommand(sublime_plugin.WindowCommand):
    def run(self, ask_arguments=False, **kwargs):
        self.ask_arguments = ask_arguments
        fabric_wrapper.configure(
            self.window.folders(),
            fab_path=get_setting(self.window, 'fab_path'),
            search_virtualenv=get_setting(self.window, 'search_virtualenv',
                                          True))
        fabfiles = fabric_wrapper.fabfiles
        if not fabfiles:
            sublime.error_message('No fabfile.py found')
            return

        try:
            errors = self.find_tasks_fabric_files(fabfiles)
        except OSError as e:
            sublime.error_message(FAB_NOT_FOUND % (fabric_wrapper.fab, e))
            return

        # Full errors go to the console; the dialog shows the last line.
        for path, error in errors:
            print('Fabric: could not list tasks of %s\n%s' % (path, error))
        summary = '\n\n'.join(
            '%s:\n%s' % (path, (str(error).strip().splitlines() or [''])[-1])
            for path, error in errors)

        if len(self.tasks):
            if errors:
                sublime.status_message(
                    'Fabric: %d fabfile(s) could not be read, see the console'
                    % len(errors))
            names_tasks = ["[%s]: %s" % x[1:] for x in self.tasks]
            self.window.show_quick_panel(names_tasks, self.execute,
                                         sublime.MONOSPACE_FONT)
        elif errors:
            sublime.error_message(
                'Fabric: could not list tasks\n\n%s\n\n'
                'Full output in the console (View > Show Console).' % summary)
        else:
            sublime.error_message('Fabric: no tasks found in:\n\n' +
                                  '\n'.join(fabfiles))

    def execute(self, index):
        if index == -1:
            return
        path, task_name = self.tasks[index][0], self.tasks[index][2]
        if self.ask_arguments:
            # deferred: opening a panel from a quick panel callback can fail
            sublime.set_timeout(
                lambda: self.ask_for_arguments(path, task_name), 10)
        else:
            self.run_task(path, task_name)

    def ask_for_arguments(self, path, task_name):
        caption = 'Arguments for %s (e.g. %s):' % (
            task_name, fabric_wrapper.arguments_example())
        self.window.show_input_panel(
            caption, last_arguments.get((path, task_name), ''),
            lambda args: self.run_task(path, task_name, args), None, None)

    def run_task(self, path, task_name, args=''):
        try:
            manager.run_task(self.window, 'utf-8', path, task_name, args)
        except OSError as e:
            sublime.error_message(FAB_NOT_FOUND % (fabric_wrapper.fab, e))
            return
        except ValueError as e:
            sublime.error_message(
                'Fabric: invalid arguments for %s\n\n%s' % (task_name, e))
            return
        if self.ask_arguments:
            last_arguments[(path, task_name)] = args

    def find_tasks_fabric_files(self, fabfiles):
        """
        Collect the tasks of every fabfile in self.tasks. A fabfile that
        fails does not hide the tasks of the others: its error is returned
        as a (path, TaskException) pair.
        """
        self.tasks = []
        errors = []
        for f in fabfiles:
            try:
                ft = fabric_wrapper.get_tasks(f)
            except TaskException as e:
                errors.append((f, e))
                continue

            if not ft:
                continue

            name = os.path.split(os.path.dirname(f))[-1]
            l = len(ft)
            self.tasks += zip([f] * l, [name] * l, ft)
        return errors


class FabEditSettingsCommand(sublime_plugin.WindowCommand):
    """ Open the default and user Fabric settings side by side. """
    def run(self):
        package = __package__ or 'Sublime-Fabric'
        self.window.run_command('edit_settings', {
            'base_file': '${packages}/%s/%s' % (package, SETTINGS_FILE),
            'default': '{\n\t$0\n}\n'})


class Listener(sublime_plugin.EventListener):
    def on_close(self, view):
        manager.close(view)
