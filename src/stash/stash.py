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

from .tree import StashTree
from .schema import schema
import os
import sys
import sqlite3
import subprocess
import webbrowser
import shutil
from collections import defaultdict

class StashError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class Field:
    """
    A Stash's view of a column in the db.stash database.
    """
    sql2keytype = {
        'varchar'  : 'text',
        'text'     : 'text',
        'integer'  : 'int',
        'date'     : 'date',
        'datetime' : 'datetime',
        'keyword'  : 'keyword',
        }

    def __init__(self, row):
        self.name, self.sqltype = row[1], row[2].lower()
        try:
            self.type = Field.sql2keytype[self.sqltype]
            return
        except KeyError:
            raise StashError('Invalid table.')

    def __repr__(self):
        return '%s (%s)'%(self.name, self.type)

class Stash:
    """
    A searchable stash of files.
    """
    def __init__(self):
        self.tree = None
        self.connection = None
        self.stashdir = None
        self.fields = []
        self.keywords = []

    def open(self, dirname):
        """
        Attach an existing stash directory.
        """
        rootdir =  os.path.join(dirname, '.stashfiles')
        database = os.path.join(dirname, 'db.stash')
        if not os.path.isdir(dirname):
            raise StashError('There is no stash named %s.'%dirname)
        elif not os.path.isdir(rootdir) or not os.path.isfile(database):
            raise StashError('The directory %s is not a valid stash.'%dirname)
        else:
            self.tree = StashTree(os.path.abspath(rootdir))
            self.connection = sqlite3.connect(database)
            self.init_fields()
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
            database = os.path.join(dirname, 'db.stash')
            os.mkdir(dirname)
            os.mkdir(rootdir)
            self.connection = sqlite3.connect(database)
            for command in schema:
                self.connection.execute(command)
            self.tree = StashTree(os.path.abspath(rootdir))
            #Hide .stashfiles on Windows
            if sys.platform == 'win32':
                os.system('attrib.exe +H %s'%rootdir)
                     
    def init_fields(self):
        """
        Find the search keys for this stash.
        """
        result = self.connection.execute('pragma table_info(files)')
        rows = result.fetchall()
        self.fields = [Field(row) for row in rows[4:]]
        result = self.connection.execute('select _keyword from keywords')
        rows = result.fetchall()
        self.keywords = [row[0] for row in rows]

    def add_field(self, field_name, field_type):
        """
        Add a new search field.
        """
        field_name = field_name.replace('"','')
        if field_type == 'keyword':
            query = """insert or ignore into keywords
                       (_keyword) values ("%s")""" % field_name
        else:
            query = 'alter table files add column "%s" %s' % (
                field_name, field_type)
        self.connection.execute(query)
        self.connection.commit()
        self.init_fields()

    def delete_field(self, field):
        """
        Delete a search field.
        """
        if field.type == 'keyword':
            query = '''select _keyword_id from keywords
                       where _keyword="%s"''' %field.name
            keyword_id = self.connection.execute(query).fetchall()[0][0]
            query = 'delete from keyword_x_file where _keyword_id=%d'%keyword_id
            self.connection.execute(query)
            query = 'delete from keywords where _keyword_id=%d'%keyword_id
            self.connection.execute(query)
            self.keywords.remove(field.name)
        else:
            query = 'alter table files drop column "%s"' % field.name
            self.connection.execute(query)
        self.connection.commit()
        self.init_fields()

    def check_hash(self, hash_string):
        query = 'Select count(*) from files where hash="%s"'%hash_string
        count = self.connection.execute(query).fetchone()[0]
        return (count == 0)

    def check_file(self, filename):
        hash_string = self.tree.hash_string(filename)
        if not self.check_hash(hash_string):
            raise StashError('That file is already stored in the stash!')
        return hash_string
        
    def insert_file(self, filename, value_dict, hash_string=None):
        """
        Insert a file into the stash.
        """
        self.tree.insert(filename, self, hash_string=hash_string)
        query = """insert into files (hash, filename, timestamp)
                   values (?, ?, datetime('now'))"""
        self.connection.execute(query,(hash_string, os.path.basename(filename)))
        self.connection.commit()
        if value_dict:
            metadata = {'hash': hash_string}
            metadata.update(value_dict)
            self.set_fields(metadata)

    def delete_file(self, hash_string):
        """
        Remove a file from the stash.
        """
        self.tree.delete(hash_string)
        query = "delete from files where hash='%s'"%hash_string
        self.connection.execute(query)
        self.connection.commit()

    def export_file(self, hash_string, export_path):
        """
        Copy a file in the stash to another location.
        """
        if os.path.exists(export_path):
            raise StashError('File exists.')
        source = open(self.tree.find(hash_string), 'rb')
        target = open(export_path, 'wb')
        while True:
            block = source.read(8192)
            if not block:
                break
            target.write(block)
        source.close()
        target.close()
    
    def view_file(self, hash_string):
        """
        Open a viewer for a file.
        """
        path = self.tree.find(hash_string)
        if sys.platform == 'darwin':
            # The webrowser module uses Preview for pdf files and Preview sets
            # the quarantine xattr whenever it is opens a file.  So far, it
            # seems to work to just clear the quarantine xattr before opening
            # the file.
            subprocess.call(['xattr', '-c', path])
        webbrowser.open_new_tab('file://%s'%path)

    def set_fields(self, value_dict):
        """
        Update the metadata for a file.
        """
        hash_string = value_dict['hash']
        query = 'select _file_id from files where hash="%s"'%hash_string
        file_id = self.connection.execute(query).fetchall()[0][0]
        query = 'select * from keywords'
        keyword_data = self.connection.execute(query).fetchall()
        keyword_ids = dict((keyword, id) for id, keyword in keyword_data)
        file_keywords = set(value_dict['keywords'])
        query = 'update files set '
        query += ', '.join(['"%s"=\'%s\''%(
            key, str(value_dict[key]).replace("'","''"))
            for key in value_dict.keys()
            if key[0] != '_' and key not in ('hash', 'keywords')])
        query += " where hash='%s'"%hash_string
        self.connection.execute(query)
        for keyword in keyword_ids:
            if keyword in file_keywords:
                query = """insert or ignore into keyword_x_file
                        (_file_id, _keyword_id)
                        values (%s, %s)"""%(file_id, keyword_ids[keyword])
            else:
                query = """delete from keyword_x_file
                        where _file_id=%s and _keyword_id=%s """%(
                            file_id, keyword_ids[keyword])
            self.connection.execute(query)
        self.connection.commit()
        
    def find_files(self, where_clause, keywords=[]):
        """ Query the stash database."""
        files_by_hash = {}
        old_factory = self.connection.row_factory
        self.connection.row_factory = sqlite3.Row
        if keywords:
            kw_clause = 'keywords._keyword in (%s) and ' % ','.join(
                ['"%s"'%kw for kw in keywords])
        else:
            kw_clause = ''
        query = """select distinct files.* from files left join
                (
                keyword_x_file inner join keywords
                on keyword_x_file._keyword_id=keywords._keyword_id
                )
            on files._file_id=keyword_x_file._file_id
            where """ + kw_clause + where_clause
        rows = self.connection.execute(query).fetchall()
        self.connection.row_factory = old_factory
        return rows

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
        old_factory = self.connection.row_factory
        self.connection.row_factory = sqlite3.Row
        result = self.connection.execute(query)
        self.connection.row_factory = old_factory
        return result.fetchall()

    def close(self):
        """
        Detach a stash directory.
        """
        if self.connection:
            self.connection.close()
            self.connection = None
        self.stashdir = None
