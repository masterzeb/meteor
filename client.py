import os

from .helpers.lists import distinct


class StaticManager(object):
    def __init__(self, static_path, libs_requirements, packages):
        self.static_path = static_path
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
            self.find_libs(package.name, True)

    def append_lib(self, path, name, ext, require=(), package=None):
        lib = StaticLib(self.static_path, path, name, ext, require, package)
        if not lib.full_name in self.libs[ext]:
            self.libs[ext][lib.full_name] = lib

    def find_libs(self, directory, is_package=False):
        path = os.path.join(self.static_path, directory)
        package = directory if is_package else None
        if os.path.exists(path):
            for filename in os.listdir(path):
                if os.path.isfile(os.path.join(path, filename)):
                    name, ext = self.parse_filename(filename)
                    require = ('meteor', ) if is_package and ext == 'js' else ()
                    self.append_lib(path, name, ext, require, package)

    def get_chain(self, ext, package=None):
        result = []
        for lib in self.libs[ext].values():
            if (package and lib.package == package) or lib.package is None:
                result.extend(self.get_lib_chain(lib.full_name, ext))
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
    def __init__(self, static_path, path, name, ext, require=(), package=None):
        self.static_path = static_path
        self.path = path
        self.name = name
        self.ext = ext
        self.require = require
        self.package = package

    @property
    def full_name(self):
        return '/'.join([self.package, self.name]) \
            if self.package else self.name

    def get_relative_path(self, minified=False):
        path = self.path.replace(self.static_path, '')
        if minified:
            result = os.path.join(
                path, 'compressed', '{0}-min.{1}'.format(self.name, self.ext))
        else:
            result = '.'.join([os.path.join(path, self.name), self.ext])
        return result.lstrip('/')

    def __str__(self):
        return self.full_name
