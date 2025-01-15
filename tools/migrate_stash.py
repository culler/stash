import os
import sys
import sqlite3
import shutil
import base62

class StashUpdater:
    def __init__(self, old_stash, new_stash):
        self.old_stash = old_stash
        self.new_stash = new_stash
        
    def update_db(self):
        old_db = os.path.join(self.old_stash, '.stashinfo')
        new_db = os.path.join(self.new_stash, 'db.stash')
        con = sqlite3.Connection(old_db)
        cur = con.cursor()
        cur.execute('select * from files')
        self.rows = [list(row) for row in cur.fetchall()]
        for row in self.rows:
            row[0] = base62.encode(int('0x' + row[0], 16))
        cur.execute('select sql from sqlite_master where '
            'type = "table" and name = "files"')
        files_schema = cur.fetchall()[0][0].split('\n')
        con.close()
        con = sqlite3.Connection(new_db)
        cur = con.cursor()        
        fields = [x.split() for x in files_schema[-1].split(',')][1:]
        for field in fields:
            name, type_name = field
            type_name = type_name.rstrip(')')
            cmd = 'alter table files add column %s %s' % (name, type_name)
            cur.execute(cmd)
        # insert rows into files table
        slots = ', '.join(['?'] * len(self.rows[0]))
        insert_cmd = 'insert into files values(NULL, %s)' % slots
        cur.executemany(insert_cmd, self.rows)
        con.commit()
        con.close()

    def move_files(self):
        old_dir = os.path.join(self.old_stash, '.stashfiles')
        new_dir = os.path.join(self.new_stash, '.stashfiles')
        old_files = os.listdir(old_dir)
        new_files = []
        for old_file in old_files:
            base, ext = os.path.splitext(old_file)
            new_base = base62.encode(int('0x' + base, 16))
            new_files.append(new_base + ext)
        heads = {x[:2] for x in new_files}
        for head in heads:
            os.makedirs(os.path.join(new_dir, head), exist_ok=True)
        for old, new in zip(old_files, new_files):
            shutil.move(
                os.path.join(old_dir, old),
                os.path.join(new_dir, new[:2], new))  
        
    def do_update(self):
        self.update_db()
        self.move_files()

def main():
    if len(sys.argv) != 3:
        print('Usage: python update_stash.py <old_stash> <new empty stash>')
        sys.exit(1)
    updater = StashUpdater(sys.argv[1], sys.argv[2])
    updater.do_update()

if __name__ == '__main__':
    main()
    
