import os

from .helpers.lists import distinct


class StaticManager(object):
    def __init__(self, static_path, libs_requirements, packages):
        self.static_path = static_path

        self.js = []
        self.css = []
        self.libs = {'js': {}, 'css': {}}

        # gather static libs with requirements
        for filename, requirements in libs_requirements.items():
            name, ext = self.parse_filename(filename)
            path = os.path.join(static_path, 'libs' \
                if ext == 'js' else 'styles')
            self.append_lib(path, name, ext, requirements)

        # gather static libs without requirements
        self.find_libs('libs')
        self.find_libs('styles')

        # gather packages static
        for package in packages:
            self.find_libs(package.name)

    def append_lib(self, path, name, ext, require=()):
        lib = StaticLib(self.static_path, path, name, ext, require)
        self.libs[ext][name] = lib
        getattr(self, ext).append(lib)

    def find_libs(self, directory):
        path = os.path.join(self.static_path, directory)
        if os.path.exists(path):
            for filename in os.listdir(path):
                if os.path.isfile(os.path.join(path, filename)):
                    name, ext = self.parse_filename(filename)
                    if not name in self.libs[ext]:
                        self.append_lib(path, name, ext)

    def get_chain(self, ext):
        libs = getattr(self, ext)
        result = []
        for lib in libs:
            result.extend(self.get_lib_chain(lib.name, ext))
        return distinct(result)

    def get_lib_chain(self, libname, ext):
        lib = self.libs[ext][libname]

        result = []
        for req in lib.require:
            result.extend(self.get_lib_chain(req, ext))

        result.append(lib)
        return distinct(result)

    def parse_filename(self, filename):
        name = ''.join(filename.split('.')[:-1])
        ext = filename.split('.')[-1]
        return name, ext


class StaticLib(object):
    def __init__(self, static_path, path, name, ext, require=()):
        self.static_path = static_path
        self.path = path
        self.name = name
        self.ext = ext
        self.require = require

    def get_relative_path(self, minified=False):
        path = self.path.replace(self.static_path, '')
        if minified:
            result = os.path.join(
                path, 'compressed', '{0}-min.{1}'.format(self.name, self.ext))
        else:
            result = '.'.join([os.path.join(path, self.name), self.ext])
        return result.lstrip('/')

    def __str__(self):
        return self.name
