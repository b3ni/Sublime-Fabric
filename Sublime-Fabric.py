import sublime
import sublime_plugin
import threading
import fabprocess
import subprocess
from Queue import Queue, Empty
from codecs import getincrementaldecoder


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
            data += packet
    except Empty:
        try:
            output = decoder.decode(data)
        except Exception:
            output = "[Fabric: decode error]\n"
        return output, True


class TaskFabric(object):
    def __init__(self, window, encoding, path, task):
        super(TaskFabric, self).__init__()
        self.window = window
        self.encoding = encoding

        self.view = self.window.new_file()
        self.view.settings().set("translate_tabs_to_spaces", False)
        self.view.settings().set("auto_indent", False)
        self.view.settings().set("smart_indent", False)
        self.view.settings().set("indent_subsequent_lines", False)
        self.view.settings().set("detect_indentation", False)
        self.view.settings().set("auto_complete", False)
        self.view.set_scratch(True)
        self.view.set_read_only(True)
        self.view.set_name("[FABRIC] [%s]" % task)

        # ejecutamos proceso
        self.fab = fabprocess.ProcessFab(path, task, encoding)

        # ejecutamos hebra de lectura
        self.q = Queue()
        self.t = threading.Thread(target=enqueue_output, args=(self.fab, self.q))
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
            edit = v.begin_edit()
            try:
                v.insert(edit, self._output_end, data)
                self._output_end += len(data)
            finally:
                v.end_edit(edit)
                v.set_read_only(True)
            v.show(self.input_region)

        if is_still_working and not self._kill:
            sublime.set_timeout(self.update_view_loop, 1000)

    def close(self):
        # si el proceso sigue vivo lo matamos
        if self.fab.is_alive():
            self.fab.kill()
        self._kill = True


class TaskManager(object):
    def __init__(self):
        self._task = {}

    def run_task(self, window, encoding, path, task_name):
        t = TaskFabric(window, encoding, path, task_name)
        self._task[t.view.id()] = t

    def close(self, view):
        if view.id() in self._task:
            t = self._task[view.id()]
            t.close()
            del self._task[view.id()]

manager = TaskManager()


class FabTasksCommand(sublime_plugin.WindowCommand):
    def __init__(self, *args, **kwargs):
        super(FabTasksCommand, self).__init__(*args, **kwargs)
        self._view = None
        self._output_end = None

    def run(self, **kwargs):
        self.find_tasks_fabric_files()

        if len(self.tasks):
            names_tasks = ["[%s]: %s" % x[1:] for x in self.tasks]
            self.window.show_quick_panel(names_tasks, self.execute, sublime.MONOSPACE_FONT)
        else:
            sublime.statusMessage('No fabfile.py found')

    def execute(self, index):
        if index != -1:
            path, task_name = self.tasks[index][0], self.tasks[index][2]
            manager.run_task(self.window, 'utf-8', path, task_name)

    def find_tasks_fabric_files(self):
        fabfiles = [subprocess.Popen(['find', folder, '-name', 'fabfile.py'], stdout=subprocess.PIPE).stdout.read() for folder in self.window.folders()]

        self.tasks = []
        for f in [f.replace('\n', '') for f in fabfiles if len(f)]:
            ft = subprocess.Popen(['fab', '-l', '-F', 'short', '-f', f], stdout=subprocess.PIPE).stdout.read().split('\n')
            ft = filter(lambda x: len(x), ft)

            if len(ft):
                name = f.split('/')[-2]
                self.tasks += zip([f] * len(ft), [name] * len(ft), ft)


class Listener(sublime_plugin.EventListener):
    def on_close(self, view):
        manager.close(view)
