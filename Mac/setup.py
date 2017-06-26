#   This file is part of the program Stash.
#   Stash helps you to stash your files, and find them later.
#
#   Copyright (C) 2010-2017 by Marc Culler and others. 
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.  In addition, python modules
#   distributed with this program may be included in works which are
#   licensed under terms compatible with version 2 of the License.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#   Project homepage: https://bitbucket.org/marc_culler/stash
#   Author homepage: http://marc-culler.info

import sys
from setuptools import setup
sys.path.append('stash')
from version import __version__
import glob

APP = ['Stash.py']
PACKAGES = ['stash']
OPTIONS = {'argv_emulation': True,
           'iconfile': 'stash_icon.icns',
           'dylib_excludes': 'Tcl.framework',
           'resources': 'doc'
}

setup(
    name = 'Stash',
    version = __version__,
    app=APP,
    packages=PACKAGES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    author = 'Marc Culler',
    url='https://bitbucket.org/marc_culler/stash',
    description = 'File stash',
    license = 'GPL',
    keywords = 'file, metadata, stash',
)
