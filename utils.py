#!/usr/bin/python3

import configparser
import os
import random
import shutil
import stat
import string
import sys

def create_app():
    if len(sys.argv) == 2:
        meteor_path = sys.path[0]
        dest = os.path.realpath(sys.argv[1])

        # make app dir
        if not os.path.exists(dest):
            os.mkdir(dest)

        # make static folders
        static_folder = os.path.join(dest, 'static')
        for folder in ('libs', 'styles', 'images'):
            path = os.path.join(static_folder, folder)
            if folder != 'images':
                path = os.path.join(path, 'compressed')
            if not os.path.exists(path):
                os.makedirs(path)

        # make app main file
        app_name = dest.split(os.path.sep)[-1]
        main_file_path = os.path.join(dest, app_name + '.py')
        with open(main_file_path, 'w') as f:
            f.write('''
#!/usr/bin/python3

# it's temporary until setup.py will be written
import sys
sys.path.append('{0}')

from meteor.core import Application
from meteor.utils import parse_args

@parse_args
def main():
    Application().run()

if __name__ == '__main__':
    main()
'''.format(os.path.dirname(meteor_path)).lstrip('\n'))

        # make main file executable
        os.chmod(main_file_path, int('777', 8))

        # make config files
        cookie_secret = ''.join(
            [random.choice(string.ascii_letters + string.digits) \
            for x in range(0, 25)]
        )
        with open(os.path.join(dest, 'config.cfg'), 'w') as f:
            f.write('''
[global]
debug = True
colored_output = True
change_builtins = True
default_locale = en
use_compressed_static = False

[server]
host = localhost
port = 8888

[database:db]
host = 127.0.0.1
port = 27017
db_name = test
gen_ids = True
safe_mode = False

[settings]
cookie_secret = {0}
'''.format(cookie_secret).lstrip('\n'))

        with open(os.path.join(dest, 'views.cfg'), 'w') as f:
            f.write('''
[global]
doctype = <!doctype html>
charset = utf-8
favicon = images/favicon.ico

[http-equiv-meta]
X-UA-Compatible = IE=Edge

[named-meta]
keywords = ('Meteor', )
'''.lstrip('\n'))


        # copy client libraries and favicon
        for f in ('meteor.js', 'jquery.js', 'favicon.ico'):
            folder = 'images' if f == 'favicon.ico' else 'libs'
            shutil.copyfile(
                os.path.join(meteor_path, 'static', f),
                os.path.join(static_folder, folder, f)
            )

        # ask for new package creation
        new_package = None
        while new_package not in ('y', 'n'):
            new_package = input('Do you want to create first package? (y/n): ')
        if new_package == 'y':
            package = input('Enter package name (leave empty for "core"): ')
            package = package or 'core'
            create_package(dest, package)
    else:
        print('Error: no destination')


def create_package(app_path, package_name):
    description = input('Enter package description: ')

    # make dirs
    path = os.path.join(app_path, package_name, 'templates')
    if not os.path.exists(path):
        os.makedirs(path)

    # define files content
    files = {
        '__init__': 'meteor_package = True\ndescription = \'{0}\'\n' \
            .format(description),
        'views': 'from meteor.handlers import View\n',
        'schemes': 'from meteor.odm.core import Document\n',
        #'forms': 'from meteor.odm.core import Form\n',
        'handlers': 'from meteor.handlers import EventHandler\n',
    }

    for k, v in files.items():
        with open(os.path.join(app_path, package_name, k + '.py'), 'w') as f:
            f.write(v)

    # add static folder
    config = configparser.ConfigParser()
    config.read(os.path.join(app_path, 'config.cfg'))
    static_path = dict(config).get('settings', {}).get('static_path',
        os.path.join(app_path, 'static'))

    package_static_path = os.path.join(static_path, package_name, 'compressed')
    if not os.path.exists(package_static_path):
        os.makedirs(package_static_path)

def parse_args(func):
    def wrapper():
        if len(sys.argv) == 3 and sys.argv[1] == '--new-package':
            create_package(sys.path[0], sys.argv[2])
        else:
            return func()
    return wrapper

if __name__ == '__main__':
    create_app()
