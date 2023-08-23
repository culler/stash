#   This file is part of the program Stash.
#   Stash helps you to stash your files, and find them later.
#
#   Copyright (C) 2010-2023 by Marc Culler and others. 
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
#   Project homepage: https://github/culler/stash
#   Author homepage: https://marc-culler.info

import os
import sys
import subprocess
import hashlib
import shutil
import base62

class Item:
    """
    Object representing a file stored in the stash.
    """
    def __init__(self, filename, source=None):
        self.source = source
        self.hash, self.extension = os.path.splitext(filename)
        self.parent = None

    def __repr__(self):
        return self.hash + self.extension

    def __cmp__(self, other):
        return cmp(self.hash, other.hash)

    def __eq__(self, other):
        return self.hash == other.hash

    def basename(self):
        """
        Return the filename associated with this leaf.
        """
        return repr(self)

    def path(self):
        """
        Return the pathname for this stash file.
        """
        return os.path.join(self.parent.path(), self.basename())

    def delete_file(self):
        """
        Delete this item's file.
        """
        remove_path = self.path()
        os.chmod(remove_path, 0o666)
        os.unlink(remove_path)

class StashTree:
    """
    A collection of files named and ordered by their base 62 encoded md5 hash.
    """

    def __init__(self, rootpath):
        self.root = os.path.abspath(rootpath)

    def hash(self, filename):
        """
        Return the base62 encoding of the md5 hash of a file.
        """
        infile = open(filename, 'rb')
        hasher = hashlib.md5()
        while True:
            block = infile.read(8192)
            if not block:
                break
            hasher.update(block)
        infile.close()
        return base62.encode(int(hasher.hexdigest(), 16))

    def insert(self, filename):
        """
        Add a new file to the stash.
        """
        name, extension = os.path.splitext(filename)
        hash = self.hash(filename)
        dir = os.path.join(self.root, hash[:2])
        os.makedirs(dir, exist_ok=True)
        path = os.path.join(dir, hash + extension)
        shutil.copy(filename, path)
        if sys.platform == 'darwin':
            print('running xattr on', path)
            result = subprocess.call(['xattr', '-c', path])
            print('result was', result)
        return hash

    def delete(self, hashname):
        """
        Delete a stashed file.
        """
        path = os.path.join(self.root, hashname[:2], hashname)

    def find(self, hash):
        """
        Return the pathname of the stashed file with the specified hash.
        """
        dir = os.path.join(self.root, hash[:2])
        for filename in os.listdir(dir):
            if filename.startswith(hash):
                return os.path.join(self.root, hash[:2], filename)
