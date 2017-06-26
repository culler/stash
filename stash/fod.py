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

class Dict(dict):
    pass

class FakeOrderedDict(Dict):
    """
    A crippled OrderedDict, but good enough for us.
    """
    def __init__(self, thing=None):
        Dict.__init__(self)
        self.keylist = []
        if isinstance(thing, list):
            for k, v in thing:
                self[k] = v
        elif hasattr(thing, 'keys'):
            for key in thing.keys():
                self[key] = thing[key]

    def __setitem__(self, key, item):
        Dict.__setitem__(self, key, item)
        if not key in self.keylist:
            self.keylist.append(key)

    def keys(self):
        return self.keylist

    def pop(self, key, default=None):
        try:
            self.keylist.remove(key)
        except ValueError:
            pass
        return Dict.pop(self, key, default)
    
    def popitem(self):
        key, value = Dict.popitem(self)
        self.keylist.remove(key)
