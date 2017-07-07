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

from .betree import BeTree
import os, sys, sqlite3, webbrowser, shutil
try:
    if sys.platform == 'darwin':
        browser = webbrowser.get('safari')
    else:
        browser = webbrowser.get()
except:
    browser = webbrowser.get()

class StashError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class SearchKey:
    """
    A Stash's view of a column in the .stashinfo database.
    """
    sql2keytype = {
        'varchar'  : 'text',
        'text'     : 'text',
        'integer'  :  'int',
        'date '    : 'date',
        'datetime' : 'datetime'}

    def __init__(self, row, fromsql=True):
        self.key, self.sqltype = str(row[1]), str(row[2])
        self.key = self.key.replace('"','')
        if fromsql:
            for type in SearchKey.sql2keytype:
                if (self.sqltype + ' ').startswith(type):
                    self.type = SearchKey.sql2keytype[type]
                    return
            raise StashError('Invalid table.')
        else:
            self.type = self.sqltype

    def __repr__(self):
        return '%s (%s)'%(self.key, self.type)

class Stash:
    """
    A searchable stash of files.
    """
    def __init__(self):
        self.tree = None
        self.connection = None
        self.stashdir = None
        self.search_keys = []

    def open(self, dirname):
        """
        Attach an existing stash directory.
        """
        rootdir =  os.path.join(dirname, '.stashfiles')
        database = os.path.join(dirname, '.stashinfo')
        if not os.path.isdir(dirname):
            raise StashError('There is no stash named %s.'%dirname)
        elif not os.path.isdir(rootdir) or not os.path.isfile(database):
            raise StashError('The directory %s is not a valid stash.'%dirname)
        else:
            self.tree = BeTree(os.path.abspath(rootdir))
            self.connection = sqlite3.connect(database)
            self.connection.row_factory = sqlite3.Row
            self.init_search_keys()
            self.stashdir = os.path.abspath(dirname)

    def create(self, dirname):
        """
        Create a new stash directory.
        """
        if os.path.lexists(dirname):
            raise StashError('The path %s is in use.'%os.path.abspath(dirname))
        else:
            self.stashdir = os.path.abspath(dirname)
            rootdir = os.path.join(dirname, '.stashfiles')
            database = os.path.join(dirname, '.stashinfo')
            os.mkdir(dirname)
            os.mkdir(rootdir)
            self.connection = sqlite3.connect(database)
            self.connection.execute("""
                create table files (
                    hash text,
                    filename text,
                    timestamp datetime)""")
            self.connection.execute("""
                create table preferences (
                    name text not null,
                    value text,
                    target text not null,
                    unique (name, target)
                    on conflict replace)""")
            self.tree = BeTree(os.path.abspath(rootdir))
            if sys.platform == 'win32': #Hide .stashfiles and .stashinfo
                os.system('attrib.exe +H %s'%rootdir)
                os.system('attrib.exe +H %s'%database)
                     
    def init_search_keys(self):
        """
        Find the search keys for this stash.
        """
        result = self.connection.execute('pragma table_info(files)')
        rows = result.fetchall()
        self.search_keys = [SearchKey(row) for row in rows[1:]]

    def add_search_key(self, key, type):
        """
        Add a new search key.
        """
        key = key.replace('"','')
        query = 'alter table files add column "%s" %s'%(key, type)
        self.connection.execute(query)
        self.connection.commit()
        self.init_search_keys()

    def insert_file(self, filename, value_dict):
        """
        Insert a file into the filesystem-based B-tree.
        """
        try:
            hash = self.tree.insert(filename)
        except ValueError:
            raise StashError('That file is already stored in the stash!')
        query = """insert into files (hash, filename, timestamp)
                   values (?, ?, datetime('now'))"""
        self.connection.execute(query,(hash, os.path.basename(filename)))
        self.connection.commit()
        if value_dict:
            self.set_search_keys(value_dict, hash)

    def delete_file(self, md5_hash):
        """
        Remove a file from the filesystem-based B-tree.
        """
        self.tree.delete(md5_hash)
        query = "delete from files where hash='%s'"%md5_hash
        self.connection.execute(query)
        self.connection.commit()

    def export_file(self, md5_hash, export_path):
        """
        Copy a file in the stash to another location.
        """
        if os.path.exists(export_path):
            raise StashError('File exists.')
        source = open(self.tree.find(md5_hash), 'rb')
        target = open(export_path, 'wb')
        while True:
            block = source.read(8192)
            if not block:
                break
            target.write(block)
        source.close()
        target.close()
    
    def view_file(self, md5_hash):
        """
        Open a viewer for a file.
        """
        browser.open_new_tab('file://%s'%self.tree.find(md5_hash))

    def set_search_keys(self, value_dict, md5_hash):
        """
        Update the metadata for a file.
        """
        query = 'update files set '
        query += ', '.join(['"%s"=\'%s\''%(key,
                                           value_dict[key].replace("'","''"))
                            for key in value_dict.keys()])
        query += " where hash='%s'"%md5_hash
        self.connection.execute(query)
        self.connection.commit()

    def find_files(self, where_clause):
        """
        Query the metadata database.
        """
        query = 'select * from files where ' + where_clause
        result = self.connection.execute(query)
        return result.fetchall()

    def set_preference(self, name, value, target='_all_'):
        """
        Save a preference in the preferences table.
        """
        query = """insert into preferences values ('%s', '%s', '%s')"""
        result = self.connection.execute(query%(name, value, target))
        self.connection.commit()

    def get_preference(self, name):
        """
        Retrieve a preference from the preferences table.
        """
        query = "select * from preferences where name='%s'"%name
        return self.connection.execute(query).fetchall()

    def close(self):
        """
        Detach a stash directory.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
        self.stashdir = None
