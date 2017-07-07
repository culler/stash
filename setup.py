#   This file is part of the program Stash.
#   Stash helps you to stash your files, and find them later.
#
#   Copyright (C) 2010 by Marc Culler and others. 
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
#   Author homepage: https://marc-culler.info

from setuptools import setup
from pkg_resources import load_entry_point
from stash.version import __version__
import os

if not os.path.exists(os.path.join('stash', 'doc', 'index.html')):
    print("""
To build the documentation:
cd documentation
make PYTHONEXE=python3 html
mv build/html ../stash/doc
""")

setup(name='Stash',
      version=__version__,
      description='File Stash',
      author='Marc Culler',
      url='https://bitbucket.org/marc_culler/stash',
      packages=['stash'],
      zip_safe=False,
      package_data = {
        'stash' : ['doc/*.*',
                   'doc/_images/*',
                   'doc/_sources/*',
                   'doc/_static/*',
                  ]
        },
      entry_points = {'console_scripts': ['stash = stash.app:main']}
)
