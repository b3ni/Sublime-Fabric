# coding: utf-8
import os
import subprocess


class Cache(object):
    def __init__(self):
        self._fab = {}
        self._fabfiles = {}
        self._key = None

    @property
    def fab(self):
        return self._get('_fab')

    @property
    def fabfiles(self):
        return self._get('_fabfiles')

    @property
    def key(self):
        if not self._key:
            _ = lambda f: os.path.split(os.path.normpath(f))[-1]
            self._key = ':'.join(_(f) for f in self.folders)
        return self._key

    def _get(self, prop_name):
        attr = getattr(self, prop_name)
        if attr.get(self.key) is None:
            attr[self.key] = getattr(self, 'find%s' % prop_name)()
        return attr[self.key]

    def _find(self, filename):
        """
        Find first fab bin in given folders.
        """
        for folder in self.folders:
            params = ['find', folder, '-name', filename]
            stdout = subprocess.Popen(params,
                                      stdout=subprocess.PIPE).stdout.read()
            found = stdout.split('\n')
            if found:
                yield found

    def set_folders(self, folders):
        self.folders = folders
        self._key = None

    def find_fab(self):
        try:
            return self._find('fab').next()[0]
        except StopIteration:
            return False

    def find_fabfiles(self):
        fabfiles = []
        map(fabfiles.extend, self._find('fabfile.py'))
        return filter(None, fabfiles)


cache = Cache()
