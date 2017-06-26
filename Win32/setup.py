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
#   Author homepage: http://marc-culler.info

from distutils.core import setup
import py2exe
from stash.version import __version__
from glob import glob

APP = [{
        'script' : 'Stash.py',
        'icon_resources' : [(1, 'stash_icon.ico')]
       }]
PACKAGES = ['stash']
OPTIONS = {'packages':'stash',
           'skip_archive':0,
           'dist_dir':'dist/Stash'}
DATAFILES = [
('doc',
  glob('../documentation/build/html/*.*')),
('doc/_static',
  glob('../documentation/build/html/_static/*.*')),
('doc/_images',
  glob('../documentation/build/html/_images/*.*')),
('doc/_sources',
  glob('../documentation/build/html/_sources/*.*'))
]

setup(
    name = 'Stash',
    version = __version__,
    windows=APP,
    data_files=DATAFILES,
    options={'py2exe': OPTIONS},
    author = 'Marc Culler',
    url = 'https://bitbucket.org/marc_culler/stash',
    description = 'File stash',
    license = 'GPL',
    keywords = 'file, metadata, stash',
)
