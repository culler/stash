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

import hashlib, os, shutil

class BeItem:
    """
    Objects of this class get stored in the leaf nodes.
    """
    def __init__(self, basename, source=None):
        self.source = source
        self.hash, self.extension = os.path.splitext(basename)
        self.parent = None

    def __repr__(self):
        return self.hash + self.extension

    def __cmp__(self, other):
        return cmp(self.hash, other.hash)

    def __eq__(self, other):
        return self.hash == other.hash

    def basename(self):
        return repr(self)

    def path(self):
        return os.path.join(self.parent.path(), self.basename())

    def rename_dir(self, old):
        """
        Rename this item's file from old to the current pathname.
        """
        new = self.path()
        if new != old:
            os.rename(old, new)

    def create_file(self):
        """
        Copy the file named self.source into the fleap.  The
        self.source attribute should be None unless this item
        represents a file being imported.
        """
        target_path = self.path()
        shutil.copyfile(self.source, target_path)
        os.chmod(target_path, 0o440)
        self.source = None

    def delete_file(self):
        """
        Remove this item's file from the fleap.
        """
        remove_path = self.path()
        os.chmod(remove_path, 0o666)
        os.unlink(remove_path)

class List(list):
    """Allows subclasses of builtin class list."""
    pass

class BeThing(List):
    """
    Parent class for internal and leaf nodes.
    """
    def sort(self):
        list.sort(self, key=lambda x : x.hash)

    def basename(self):
        return self.hash

    def address(self):
        """
        Return the address of this node from the root.
        """
        if self.parent is None:
            return []
        else:
            return self.parent.address() + [self.parent.index(self)]

    def path(self):
        """
        Return the path of this node from the root.
        """
        if self.parent is None:
            return self.rootpath
        else:
            return os.path.join(self.parent.path(), self.hash)

    def predecessor(self):
        """
        Return the preceding node on the same level,
        or None if this is the first node on the level.
        """
        if self.parent is None:
            return None
        n = self.parent.index(self)
        if n != 0:
            return self.parent[n-1]
        else:
            parent_pred = self.parent.predecessor()
            if parent_pred is None:
                return None
            else:
             return parent_pred[-1]

    def successor(self):
        """
        Return the subsequent node on the same level,
        or None if this is the last node on the level.
        """
        if self.parent is None:
            return None
        n = self.parent.index(self)
        if n != len(self.parent) - 1:
            return self.parent[n+1]
        else:
            parent_succ = self.parent.successor()
            if parent_succ is None:
                return None
            else:
             return parent_succ[0]

    def hash_up(self):
        """
        Recompute the hash for this node and its ancestors.  The hash of
        a node is the maximum of the hashes of its children.  For a fleap,
        the hash is the same as the directory name or file basename.
        """
        try:
            newhash = self[-1].hash
        except IndexError:
            return
        node = self
        while True:
            parent = node.parent
            if node.hash != newhash:
                old = node.path()
                node.hash = newhash
                if parent:
                    node.rename_dir(old)
            if parent is None or parent.index(node) != len(parent) - 1:
                break
            node = parent

    def kidnap(self, other, N):
        """
        Take N many of other's children, preserving order.  If
        other's largest child is less than self's smallest, take them
        from the large end of other and insert them in the small end
        of self.  Otherwise (even if len(self) == 0) do the opposite.
        """
        if len(self) > 0 and other[-1] < self[0]:
            for n in range(N):
                node = other.pop()
                old = node.path()
                self.insert(0, node)
                node.parent = self
                node.rename_dir(old)
        else:
            for n in range(N):
                node = other.pop(0)
                old = node.path()
                self.append(node)
                node.parent = self
                node.rename_dir(old)

    def split(self):
        """
        If the size of this node is >= 2*minsize, the leftmost minsize
        children are transfered to a new node, which is inserted as a
        sibling of this one.  This may increase the size of the
        parent.  So, split the parent.
        """
        if len(self) < 2*BeTree.minsize:
            return
        if self.parent is None:
            self.add_rootdir()
            self.parent = BeNode([], parent=None, rootpath=self.rootpath)
            self.parent.append(self)
            self.parent.hash = self.hash
        new = self.new_sib()
        self.parent.insert(self.parent.index(self), new)
        # this is required to get the correct directory name
        new.hash = self[BeTree.minsize-1].hash
        new.create_dir()
        new.kidnap(self, BeTree.minsize)
        self.parent.split()

    def merge(self):
        """
        If this (non-root) node is too small, steal children from an
        adjacent node at the same level.  If the adjacent node is
        larger than minsize, take one child.  Otherwise take them
        all and remove the adjacent node.  This may make the parent
        too small, so merge the parent.
        """
        if self.parent is None or not len(self) < BeTree.minsize:
            return
        node = self.predecessor()
        if node is None:
            node = self.successor()
        if node is None:
            raise RuntimeError('Invalid Btree')
        if len(node) == BeTree.minsize:
            self.kidnap(node, BeTree.minsize)
            self.remove_dir(node)
            node.parent.remove(node)
            node.parent.hash_up()
        else:
            self.kidnap(node, 1)
            node.hash_up()
        self.hash_up()
        node.parent.merge()

    def rename_dir(self, oldname):
        """
        Rename this node's directory from oldname to the current pathname.
        """
        newname = self.path()
        if newname != oldname:
            if newname.count('/') != oldname.count('/'):
                raise RuntimeError
            os.rename(oldname, newname)

    def remove_dir(self, node):
        """
        Remove this node's directory.
        """
        os.rmdir(node.path())

    def create_dir(self):
        """
        Create this node's directory.
        """
        os.mkdir(self.path())

    def add_rootdir(self):
        """
        Create a new root directory and move this node's directory
        into it as a subdirectory.
        """
        if self.parent:
            raise RuntimeError
        rootpath = self.rootpath
        rootparent = os.path.abspath(os.path.join(rootpath, os.path.pardir))
        temppath = os.path.join(rootparent, self.hash)
        newpath = os.path.join(rootpath, self.hash)
        os.rename(rootpath, temppath)
        os.mkdir(rootpath)
        os.rename(temppath, newpath)

    def del_rootdir(self):
        """
        Destroy the root directory, whose only subdirectory corresponds to
        this node, and replace it by this node's directory.
        """
        rootpath = self.rootpath = self.parent.rootpath
        rootparent = os.path.abspath(os.path.join(rootpath, os.path.pardir))
        temppath = os.path.join(rootparent, self.hash)
        os.rename(self.path(), temppath)
        os.rmdir(rootpath)
        os.rename(temppath, rootpath)

class BeNode(BeThing):
    """
    An internal node.
    """
    def __init__(self, list_of_lists, parent=None, rootpath=None):
        self.parent = parent
        if parent is None:
            self.rootpath = rootpath
        if list_of_lists:
            first = list_of_lists[0]
            if isinstance(first[0], list):
                self += [BeNode(x, parent=self) for x in list_of_lists]
            else:
                self += [BeLeaf(x, parent=self) for x in list_of_lists]
            self.sort()
            self.hash = max([x.hash for x in self])
        else:
            self.hash = ''

    def new_sib(self):
        return BeNode([], parent=self.parent)

    def as_list(self):
        """
        Return a list of all items descended from this node.
        """
        result = []
        for node in self:
            result += node.as_list()
        return result

    def depth(self):
        """
        The depth of the tree of descendents of this node:
        """
        return 1 + self[0].depth()

    def pr(self, terms):
        terms.append('[')
        for node in self:
            node.pr(terms)
        terms.append(']')

    def validate(self):
        """
        Every node except the root should have between minsize and 2*minsize-1
        children.  The hash of every node should equal the maximum hash of its
        children.  The children should be ordered by hash.  Each child should
        know its parent.
        """
        assert self.hash == self[-1].hash, str(self)
        first = [x.hash for x in self]
        second = [x.hash for x in self]
        second.sort()
        assert first == second, str(self)
        for node in self:
            assert node.parent == self, str(self)
            assert len(self) >= BeTree.minsize or self.parent is None, str(self)
            node.validate()

    def insert_item(self, item):
        for node in self:
            if item.hash <= node.hash: break
        node.insert_item(item)

    def delete_item(self, item):
        for node in self:
            if item.hash <= node.hash: break
        node.delete_item(item)
        if len(self) == 1:
            newroot = self[0]
            newroot.del_rootdir()
            newroot.parent = None
            return newroot
        else:
            return None

    def find(self, item):
        """
        Search from this node for an item with the same hash as the input.
        Return the found item, or None.
        """
        for node in self:
            if node.hash >= item.hash: break
        return node.find(item)

class BeLeaf(BeThing):
    """
    A leaf node.
    """
    def __init__(self, list_of_strings, parent=None, rootpath=None):
        self.parent = parent
        if parent is None:
            self.rootpath = rootpath
        self += [BeItem(x) for x in list_of_strings]
        for item in self:
            item.parent = self
        if len(self) > 0:
            self.hash = max([x.hash for x in self])
        else:
            self.hash = ''

    def new_sib(self):
        return BeLeaf([], parent=self.parent)

    def as_list(self):
        return list(self)

    def depth(self):
        return 0

    def pr(self, terms):
        terms.append('[')
        for item in self:
            terms.append(repr(item))
        terms.append(']')

    def validate(self):
        if self.parent is not None:
            assert len(self) >= BeTree.minsize, str(self)
        if len(self) > 0:
            assert self.hash == self[-1].hash, str(self)

    def insert_item(self, item):
        if item in self:
            raise ValueError('Insertion of existing item.')
        self.append(item)
        item.parent = self
        item.create_file()
        self.sort()
        self.hash_up()
        self.split()

    def delete_item(self, fake_item):
        try:
            n = self.index(fake_item)
        except ValueError:
            raise ValueError('Deletion of non-existent item.')
        self.pop(n).delete_file()
        self.hash_up()
        self.merge()

    def find(self, item):
        """
        Return the item with the same hash as the input, or None if not
        found.
        """
        try:
            return self[self.index(item)]
        except ValueError:
            return None

class BeTree:
    """
    A B+tree, mirrored in the filesystem.  Files are named and ordered
    by their md5 hex digest.
    """
    minsize = 128

    def __init__(self, rootpath):
        absrootpath = os.path.abspath(rootpath)
        list_of_lists = self.dirtree(rootpath)
        if not list_of_lists:
            self.root = BeLeaf([], parent=None, rootpath=absrootpath)
        elif isinstance(list_of_lists[0], list):
            self.root = BeNode(list_of_lists, rootpath=absrootpath)
        else:
            self.root = BeLeaf(list_of_lists, rootpath=absrootpath)

    def __repr__(self):
        terms = []
        result = ''
        self.root.pr(terms)
        indent = ''
        for term in terms:
            if term.startswith('['):
                result += indent + term + '\n'
                indent += ' '
            elif term == ']':
                indent = indent[:-1]
                result += indent + '],\n'
            else:
                result += indent + "'" + term + "',\n"
        return result[:-2]

    def __len__(self):
        return len(self.root.as_list())

    def depth(self):
        return self.root.depth()

    def validate(self):
        self.root.validate()

    def md5(self, filename):
        infile = open(filename, 'rb')
        hasher = hashlib.md5()
        while True:
            block = infile.read(8192)
            if not block:
                break
            hasher.update(block)
        infile.close()
        return hasher.hexdigest()

    def insert(self, filename):
        name, extension = os.path.splitext(filename)
        digest = self.md5(filename)
        item = BeItem(digest + extension, source=os.path.abspath(filename))
        self.root.insert_item(item)
        if self.root.parent:
            self.root = self.root.parent
        return digest

    def delete(self, filename):
        newroot = self.root.delete_item(BeItem(filename))
        if newroot:
            self.root = newroot

    def find(self, hash):
        """
        Return the pathname of the file with the specified hash (or basename).
        """
        return self.root.find(BeItem(hash)).path()

    def dirtree(self, path):
        """
        Represent the structure of a directory as a list of lists.
        """
        if os.path.isfile(path):
            return os.path.basename(path)
        else:
            children = [x for x in os.listdir(path) 
                        if os.path.exists(os.path.join(path, x))]
            children.sort()
            return [self.dirtree(os.path.join(path,x)) for x in children]
