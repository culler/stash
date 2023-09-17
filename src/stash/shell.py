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

from .stash import *
import tempfile, subprocess

class StashShell:
    """
    A command-line interface to a Stash.
    """
    def __init__(self):
        self.stash = Stash()
        self.state = 'stash'
        self.current_file = None
    
    def quit(self):
        self.stash.close()
        sys.exit()

    def show_keys(self):
        print('Search Keys:\t'+
              '\n\t\t'.join([str(x) for x in self.stash.search_keys]))

    def process_input(self, typed):
        if typed.startswith('q'):
            self.quit()
        elif self.state == 'stash':
            if typed.startswith('o'):
                try:
                    path = raw_input('Path to stash: ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                print('Opening %s'%path)
                self.stash.open(path)
                self.state = 'ready'
                self.show_keys()
            elif typed.startswith('n'):
                try:
                    path = raw_input('Path to new stash: ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                print('Creating new stash %s'%path)
                self.stash.create(path)
                print('Now you should add some search keys.')
                self.state = 'manage keys'
            else:
                print('Command not recognized.')
        elif self.state == 'ready':
            if typed.startswith('c'):
                print('Closing stash.')
                self.stash.close()
                self.state = 'stash'
            elif typed.startswith('i'):
                try:
                    filename = raw_input('Filename to import: ').rstrip()
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                print('Importing %s'%filename)
                value_dict = {}
                for key in self.stash.search_keys[2:]:
                    value_dict[key.key] = raw_input('%s = '%key)
                try:
                    self.stash.insert_file(filename, value_dict)
                except IOError:
                    raise StashError('Could not open file.')
                except ValueError:
                    raise StashError('That file is already in the stash.')
            elif typed.startswith('f'):
                try:
                    search = raw_input('Find files matching:  ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                print('Finding files matching %s'%search)
                rows = self.stash.find_files(self.match_clause(search))
                if len(rows) == 0:
                    print('No files were found.')
                    return
                if self.choose_file(rows) is None:
                    return
                else:
                    self.state = 'file'
            elif typed.startswith('m'):
                print('Manage key structure')
                self.state = 'manage keys'
            elif typed.startswith('s'):
                try:
                    search = raw_input('Select * from files where ... ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                print('Finding files where %s'%search)
                rows = self.stash.find_files(search)
                if len(rows) == 0:
                    print('No files were found.')
                if self.choose_file(rows) is None:
                    return
                else:
                    self.state = 'file'
            else:
                print('Command not recognized.')
        elif self.state == 'manage keys':
            if typed.startswith('a'):
                print('Adding a key.')
                try:
                    key = raw_input('Key name: ')
                    type = raw_input('Key type: ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                self.stash.add_search_key(key, type)
            elif typed.startswith('r'):
                print('Removing keys is not supported yet.')
                print('(No "alter table drop column" in sqlite.)')
            elif typed.startswith('s'):
                self.show_keys()
            elif typed.startswith('u'):
                print('Done.')
                self.state = 'ready'
            else:
                print('Command not recognized.')
        elif self.state == 'file':
            if typed.startswith('d'):
                print('Deleting file:')
                print(' | '.join(tuple(self.current_file)[2:]))
                try:
                    raw_input('Hit Enter to continue, ^C to cancel.')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                self.stash.delete_file(self.current_file[0])
                self.state = 'ready'
            elif typed.startswith('e'):
                print('Exporting file: %s'%self.current_file['filename'])
                try:
                    export_path = raw_input('Path to exported file: ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    return
                self.stash.export_file(self.current_file['hash'], export_path)
            elif typed.startswith('k'):
                print('Editing search keys.')
                self.edit_keys()
            elif typed.startswith('v'):
                print('Viewing file.')
                self.stash.view_file(self.current_file['hash'])
            elif typed.startswith('u'):
                print('Done.')
                self.state = 'ready'
            else:
                print('Command not recognized.')

    prompts = {
               'stash': '(n)ew, (o)pen, (q)uit',
               'ready': '(c)lose, (i)mport, (f)ind, (m)anage, (s)ql, (q)uit',
         'manage keys': '(a)dd, (r)emove, (s)how, (u)p, (q)uit', 
                'file': '(d)elete, (e)xport, (k)eys, (v)iew, (u)p, (q)uit'
               }

    def match_clause(self, match):
        terms = match.split()
        if len(terms) == 0:
            return '1'
        booleans = []
        for term in terms:
            for column in self.stash.search_keys[2:]:
                booleans.append("%s like '%%%s%%'"%(column.key, term))
        return ' or '.join(booleans)

    def choose_file(self, query_result):
                n = 0
                for row in query_result:
                    values = tuple(row)[3:]
                    if len(values) == 0:
                        values = row['filename']
                    print('%s\t'%n, ' :: '.join(values))
                    n += 1
                try:
                    index =  raw_input('Select a file: ')
                except KeyboardInterrupt:
                    print(' - Cancelled')
                    self.state = 'ready'
                    return
                if not index.strip():
                    return None
                try:
                    self.current_file = query_result[int(index)]
                except (IndexError, TypeError, ValueError):
                    raise StashError('Invalid index')
                return index

    def edit_keys(self):
        dictstr = '{\n'
        for key in list(self.current_file.keys())[3:]:
            value = self.current_file[key].replace("'",r"\'")
            dictstr += "'%s' : '%s',\n"%(key, value)
        dictstr += '}\n'
        fd, temppath = tempfile.mkstemp(dir=self.stash.stashdir)
        temp = os.fdopen(fd, 'w')
        temp.write(dictstr)
        temp.close()
        subprocess.call(['nano', temppath])
        temp = open(temppath)
        dictstr = temp.read()
        temp.close()
        os.unlink(temppath)
        exec('value_dict = ' + dictstr)
        self.stash.set_search_keys(value_dict, self.current_file['hash'])
        
    def loop(self):
        if len(sys.argv) > 1:
            self.stash.open(sys.argv[1])
            self.state = 'ready'
        while True:
            try:
                print(StashShell.prompts[self.state])
                typed = raw_input(self.state + '> ')
            except EOFError:
                print('\r')
                quit()
            except KeyboardInterrupt:
                print(' - Cancelled')
                continue
            try:
                self.process_input(typed)
            except StashError as E:
                print('\n', '**** Stash Error:', E.value, '\n')
            except sqlite3.OperationalError as sql:
                print('Sqllite Error:', sql)

def main():
    shell = StashShell()
    shell.loop()

if __name__ == '__main__':
    main()
