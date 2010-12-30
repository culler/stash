#!/usr/bin/python

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
#   EMAIL: culler@users.sourceforge.net
#   URL:  http://sourceforge.net/projects/filestash

import os, sys

from stash.version import version
print('Cleaning out old stuff for a clean build.')
os.system('rm -rf build dist')

print('Building version %s.'%version)
basename = 'Stash-%s'%version
os.system('python setup.py py2app')

print('Throwing away garbage.')
resource_dir = 'dist/Stash.app/Contents/Frameworks/Tk.framework/Resources/'
os.system('rm -rf %s'%os.path.join(resource_dir, 'Wish.app'))

print('Removing old disk image.')
try:
    os.remove('%s.dmg'%basename)
except OSError:
    pass

print('Checking %s.'%basename)
if not os.path.exists(basename):
    os.symlink('dist', basename)
elif not os.path.islink(basename):
    print('%s should be a link!'%basename)
    sys.exit(-1)

print('Removing old eggs.')
os.system('rm %s'%os.path.join(basename, '*.egg'))
print('Building disk image.')
os.system('hdiutil create -srcfolder %s %s.dmg'%(basename, basename))

print('Building new egg')
os.system('python setup.py bdist_egg')
