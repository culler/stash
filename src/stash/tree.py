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
        self.hash_string, self.extension = os.path.splitext(filename)
        self.parent = None

    def __repr__(self):
        return self.hash_string + self.extension

    def __cmp__(self, other):
        return cmp(self.hash_string, other.hash_string)

    def __eq__(self, other):
        return self.hash_string == other.hash_string

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

    def hash_string(self, filename):
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

    def insert(self, filename, stash, hash_string=None):
        """
        Add a new file to the stash.  If the hash is provided it will
        be used, instead of computing the hash.
        """
        name, extension = os.path.splitext(filename)
        if hash_string is None:
            hash_string = self.hash_string(filename)
            if not stash.check_hash(hash_string):
                raise ValueError('Hash is in use already.')
        dir = os.path.join(self.root, str(hash_string[:2]))
        os.makedirs(dir, exist_ok=True)
        path = os.path.join(dir, hash_string + extension)
        if not os.path.exists(path):
            shutil.copy(filename, path)
        else:
            raise ValueError('File exists.')
        return hash_string

    def delete(self, hash_string):
        """
        Delete a stashed file.
        """
        dir = os.path.join(self.root, hash_string[:2])
        for filename in os.listdir(dir):
            if filename.startswith(hash_string):
                break
        else:
            return
        os.unlink(os.path.join(dir, filename))

    def find(self, hash_string):
        """
        Return the pathname of the stashed file with the specified hash.
        """
        dir = os.path.join(self.root, hash_string[:2])
        for filename in os.listdir(dir):
            if filename.startswith(hash_string):
                return os.path.join(self.root, hash_string[:2], filename)
