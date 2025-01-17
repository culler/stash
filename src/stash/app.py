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
#   Project homepage: https://bitbucket.org/marc_culler/stash
#   Author homepage: https://marc-culler.info

import os
import sys
import time
import subprocess
import json
import plistlib
from collections import OrderedDict
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.messagebox import showerror, showwarning, showinfo
from tkinter.simpledialog import Dialog
from urllib.request import pathname2url
from .theme import StashStyle
from .stash import Stash, Field, StashError, __file__ as stashfile
from .browse import browser
from . import __version__

if sys.platform == 'darwin':
    if sys.path[0].endswith('Resources'):
        stash_doc_path = os.path.join(sys.path[0], os.path.pardir,
                                      'doc', 'index.html')
    elif sys.path[0].endswith('.zip'):
        base = os.path.abspath(os.path.join(sys.path[0]))
        bundle = os.path.abspath(os.path.join(base, os.path.pardir,
                                              os.path.pardir))
        stash_doc_path = os.path.join(bundle, 'doc', 'index.html')
    else:
        stash_doc_path = os.path.join(os.path.dirname(stashfile),
                                      'doc', 'index.html')
else:
  stash_doc_path = os.path.abspath(os.path.join(os.path.dirname(stashfile), 'doc', 'index.html'))

if sys.platform == 'darwin':
    selected_bg = 'systemSelectedTextBackgroundColor'
else:
    selected_bg = '0xaaaaff'  # FIX ME
    
class Scrollbar(tk.Scrollbar):
    """
    Scrollbar that removes itself when not needed.
    """
    # http://effbot.org/zone/tkinter-autoscrollbar.htm
    def set(self, lo, hi):
        if float(lo) <= 0.0 and float(hi) >= 1.0:
            # grid_remove is currently missing from tkinter!
            self.tk.call("grid", "remove", self)
        else:
            self.grid()
        tk.Scrollbar.set(self, lo, hi)
    def pack(self, **kw):
        raise tk.TclError("cannot use pack with this widget")
    def place(self, **kw):
        raise tk.TclError("cannot use place with this widget")

class Listbox(tk.Listbox):
    """
    A Listbox who tells the scrollbar who is calling.
    """
    # This allows the StashViewer to synchronize the lists if
    # one list is scrolled by using the mouse wheel.
    def yscroll(self, lo, hi):
        self.viewer.scrollbar_set(self, lo, hi)

class StashViewer():
    def __init__(self, app, directory):
        self.app = app
        self.stash_dir = directory
        self.stash_name = os.path.basename(directory)
        self.curdir = directory
        self.window = window = tk.Toplevel(app.root, class_='stash')
        window.title(self.stash_name)
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.grid_columnconfigure(0, weight=1)
        window.grid_rowconfigure(1, weight=1)
        window.bind("<Return>", self.match)
        self.stash = Stash()
        self.stash.open(directory)
        prefs = self.stash.get_preference('geometry')
        saved_geometry = prefs[0]['value'] if prefs else None
        fields = self.stash.fields
        self.columns = columns = [x.name for x in fields]
        self.selected = None
        self.style = StashStyle(window)
        self.panes = {}
        topframe = ttk.Frame(window)
        topframe.grid(row=0, columnspan=2, sticky=tk.EW)
        gobutton = ttk.Button(topframe,
                             text='Show Files',
                             command=self.match)
        gobutton.grid(row=0, column=0, sticky=tk.W+tk.S, padx=2)
        keyword_label = ttk.Label(topframe, text='with')
        keyword_label.grid(row=0, column=1, sticky=tk.E)
        keyword_var = tk.StringVar(window)
        keyword_var.set('Keywords')
        keyword_menu = tk.Menu(topframe)
        self.keyword_vars = {}
        for keyword in self.stash.keywords:
            var = tk.IntVar(window)
            keyword_menu.add_checkbutton(label=keyword, variable=var)
            self.keyword_vars[keyword] = var
        self.keyword_button = ttk.Menubutton(topframe, text='keywords',
            menu=keyword_menu)
        self.keyword_button.grid(row=0, column=2, sticky=tk.W, ipady=2)
        order_label = ttk.Label(topframe, text='sorted by')
        order_label.grid(row=0, column=3, sticky=tk.E)
        columns = self.columns
        self.order_var = order_var = tk.StringVar(window)
        order_var.set('timestamp')
        self.order_menu = order_menu = tk.Menu(topframe)
        for item in ['timestamp'] + columns:
            order_menu.add_radiobutton(label=item, variable=order_var)
        self.order_button = ttk.Menubutton(topframe, textvariable=order_var,
            menu=order_menu)
        self.order_button.grid(row=0, column=4, sticky=tk.W)
        self.direction_var = direction_var = tk.StringVar(window)
        self.direction = direction = ttk.OptionMenu(topframe, direction_var,
            'descending', 'descending', 'ascending')
        direction.grid(row=0, column=5, sticky=tk.W)
        topframe.grid_columnconfigure(5, weight=1)
        self.mainlist = mainlist = tk.PanedWindow(window,
                                                  borderwidth=0,
                                                  sashpad=0,
                                                  sashwidth=8,
                                                  handlesize=8,
                                                  handlepad=6,
                                                  showhandle=True,
                                                  sashrelief=tk.RAISED,
                                                  relief=tk.FLAT)
        self.scrollbar = scrollbar = Scrollbar(window)
        self.listboxes = {}
        self.filters = {}
        for column in self.columns:
            self.add_pane(column)
        scrollbar.config(command=self.yview)
        mainlist.grid(row=1, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=1, column=1, sticky=tk.NS)
        spacer = ttk.Frame(window, height=2, borderwidth=0)
        spacer.grid(row=2, columnspan=2, sticky=tk.EW)
        self.status = status = tk.StringVar(self.window)
        statusbox = tk.Entry(self.window,
                             state=tk.DISABLED,
                             foreground='red',
                             disabledforeground='red',
                             textvariable=status,
                             relief=tk.FLAT)
        statusbox.grid(row=3, column=0, sticky=tk.EW, padx=20)
        self.menubar = menubar = tk.Menu(window)
        menubar = tk.Menu(self.window)
        Application_menu = tk.Menu(menubar, name="apple")
        menubar.add_cascade(label='Stash', menu=Application_menu)
        File_menu = tk.Menu(menubar, name="file")
        File_menu.add_command(label='Configure...', command=self.configure)
        menubar.add_cascade(label='File', menu=File_menu)
        Action_menu = tk.Menu(menubar, name='action')
        menubar.add_cascade(label='Action', menu=Action_menu)
        Window_menu = tk.Menu(menubar, name='window')
        menubar.add_cascade(label='Window', menu=Window_menu)
        Application_menu.insert_command(0, label='About Stash ...',
            command=self.app.about)
        Application_menu.insert_separator(0)
        File_menu.add_command(label='Open...'+scut['Open'],
                              command=self.app.open)
        File_menu.add_command(label='New...'+scut['New'], command=self.app.new)
        
        Action_menu.add_command(label='Import...', command=self.import_file)
        Action_menu.add_command(label='Export...', command=self.export_file)
        Action_menu.add_command(label='Remove...', command=self.remove_file)
        Action_menu.add_command(label='Metadata...', command=self.metadata)
        Help_menu = tk.Menu(menubar, name="help")
        menubar.add_cascade(label='Help', menu=Help_menu)
        if sys.platform != 'darwin':
            Application_menu.add_command(label='Quit Stash'+scut['Quit'],
                command=self.app.quit)
            Help_menu.add_command(label='Stash Help', command=self.app.help)
        window.config(menu=menubar)
        if saved_geometry:
            window.geometry(saved_geometry)
        window.update_idletasks()
        self.set_sashes()
        window.update_idletasks()
        self.match()

    def update_keyword_menu(self):
        keyword_menu = self.keyword_button['menu']
        keyword_menu.delete(0, tk.END)
        self.keyword_vars = {}
        for keyword in self.stash.keywords:
            var = tk.IntVar(self.window)
            keyword_menu.add_checkbutton(label=keyword, variable=var)
            self.keyword_vars[keyword] = var

    def add_pane(self, column):
        # needs a minimum size if the lists are empty
        pane = ttk.PanedWindow(self.mainlist, orient=tk.VERTICAL)
        label = ttk.Label(pane, text=column, padding=(5,0))
        filter = ttk.Entry(pane)
        listbox = Listbox(pane, height=10, borderwidth=0,
            background='systemTextBackgroundColor',
            selectmode=tk.SINGLE)
        listbox.viewer = self
        listbox.config(yscrollcommand = listbox.yscroll)
        listbox.bind('<Button-1>', self.select_row)
        listbox.bind('<Double-Button-1>', self.double_click)
        self.listboxes[column] = listbox
        self.filters[column] = filter
        pane.rowconfigure(2, weight=1)
        pane.columnconfigure(0, weight=1)
        label.grid(row=0, column=0, sticky=tk.EW)
        filter.grid(row=1, column=0, sticky=tk.EW)
        listbox.grid(row=2, column=0, sticky=tk.NSEW, padx=5)
        self.mainlist.add(pane)
        self.mainlist.paneconfigure(pane, padx=0, pady=0)
        self.panes[column] = pane

    def set_sashes(self):
        pref = self.stash.get_preference('sashes')
        try:
            pref_value = pref[0]['value']
        except IndexError:
            return
        if pref_value:
            coords = pref_value.split(':')
            for N in range(len(coords) - 1, -1, -1):
                self.window.update()
                try:
                    self.mainlist.sash_place(N, coords[N], 0)
                except tk.TclError:
                    print('Failed to place sash')
                    pass

    def activate(self):
        self.window.deiconify()
        self.window.focus_force()

    def close(self):
        self.stash.set_preference('geometry', self.window.geometry())
        # This is tricky if the number of columns has changed.
        sashes = []
        N = 0
        while True:
            try:
                sashes.append(str(self.mainlist.sash_coord(N)[0]))
                N += 1
            except tk.TclError:
                break
        self.stash.set_preference('sashes', ':'.join(sashes))
        self.stash.close()
        self.app.close_viewer(self)
        self.window.destroy()

    def scrollbar_set(self, widget, lo, hi):
        newtop = widget.nearest(0)
        for listbox in self.listboxes.values():
            listbox.yview(newtop)
        self.scrollbar.set(lo, hi)

    def yview(self, scroll, number, units=None):
        for listbox in self.listboxes.values():
            listbox.yview(scroll, number, units)

    def select_row(self, event):
        index = event.widget.index('@%s,%s'%(event.x, event.y))
        if index < 0:
            return
        # If a row is selected in one column, select the same row
        # in all columns
        if not self.selected is None:
            for listbox in self.listboxes.values():
                listbox.itemconfig(self.selected, bg='')
        for listbox in self.listboxes.values():
            listbox.itemconfig(index, bg=selected_bg)
        self.selected = index
            
    def double_click(self, event):
        self.select_row(event)
        if not self.selected is None:
            self.stash.view_file(self.search_result[self.selected]['hash'])
        #return 'break'

    def display_results(self):
        self.selected = None
        for column in self.columns:
            self.listboxes[column].delete(0,tk.END)
        count = 0
        for row in self.search_result:
            for column in self.columns:
                box = self.listboxes[column]
                box.insert(tk.END, row[column] or '')
            count += 1
        self.status.set('%d file%s found.'%(count, '' if count==1 else 's'))

    def match_info(self):
        filters = []
        columns = self.stash.fields
        fields = ['timestamp'] + [column.name for column in columns]
        first = self.order_var.get()
        if first in fields:
            fields.remove(first)
            fields.insert(0, first)
        order_terms = ['`%s`'%field for field in fields]
        if self.direction_var.get() == 'descending':
            order_terms[0] = order_terms[0] + ' desc'
        if order_terms:
            order_by = ' order by ' + ', '.join(order_terms)
        else:
            order_by = ''
        selected_keywords = [k for k in self.stash.keywords
            if self.keyword_vars[k].get()]
        for column in self.columns:
            filter = self.filters[column].get()
            if not filter:
                continue
            terms = filter.split()
            for term in terms:
                filters.append("%s like '%%%s%%'"%(column, term))
        if not filters:
            where_clause = '1' + order_by
        else:
            where_clause = ' and '.join(filters) + order_by
        return where_clause, selected_keywords

    def match(self, event=None):
        where, keywords = self.match_info()
        self.search_result = self.stash.find_files(where, keywords)
        self.display_results()

    def clear_status(self):
        self.status.set('')

    def import_file(self):# Could accept many files?
        self.status.set('Import file.')
        filename = askopenfilename(title='Choose a file to import',
                                       filetypes=[('All files', '*')])
        if filename is None or filename=='':
            self.status.set('Import cancelled.')
            self.window.after(1000, self.clear_status)
            return
        if not os.path.isfile(filename):
            showerror('Import File', '%s is not a file.'%filename)
        self.curdir = os.path.dirname(filename)
        if sys.platform == 'darwin':
            subprocess.call(['xattr', '-c', filename])
        try:
            hash_string = self.stash.check_file(filename)
        except StashError as E:
            showerror('Import File', E.value)
            return
        browser.open_new_tab('file://%s'%pathname2url(filename))
        metadata = OrderedDict([(x, '') for x in self.columns])
        dialog = MetadataEditor(self.window, metadata, self.stash.keywords,
                                    'Create Metadata')
        if dialog.result is None:
            self.status.set('Import cancelled')
            self.window.after(1000, self.clear_status)
            return
        if sys.platform == 'darwin':
            # Give preview some time to do its mischief
            time.sleep(1)
            subprocess.call(['xattr', '-c', filename])
        try:
            self.stash.insert_file(filename, dialog.result, hash_string)
        except StashError as E:
            showerror('Import File', E.value)
        self.status.set('')
        self.match()

    def export_file(self, index=None):
        self.status.set('Exporting file.')
        if index is None:
            if self.selected is None:
                showerror('Export Files', 'Please select a file.')
                return
            else:
                index = self.selected
                self.selected = None
        row = self.search_result[index]
        self.status.set('')
        return self.export_the_file(row)

    def export_the_file(self, row):
        default_filename = row['filename']
        default_extension = os.path.splitext(default_filename)[1]
        filename = asksaveasfilename(parent=self.window,
                                     initialfile=default_filename,
                                     initialdir=self.stash_dir,
                                     defaultextension=default_extension,
                                     title='Choose an export name')
        if filename is None or filename == '':
            return
        self.curdir = os.path.dirname(filename)
        try:
            self.stash.export_file(row['hash'], filename)
        except StashError as E:
            showerror('Export File', 'Stash will not overwrite existing files.')
            return None
        return filename

    def remove_file(self):
        self.status.set('Remove file.')
        if self.selected is None:
            showerror('Remove File', 'Please select a file.')
            return
        index = self.selected
        self.selected = None
        row = self.search_result[index]
        dialog = RemoveQuestion(self.window, row, title='Remove File')
        if dialog.result is None:
            self.status.set('Removal cancelled.')
            self.window.after(1000, self.clear_status)
            return
        if dialog.result['export first']:
            filename = self.export_file(index=index)
            if filename is None:
                    return
        if dialog.result['save metadata']:
            metadata = dict(row)
            for key in ('_file_id', 'hash', 'filename', 'timestamp'):
                metadata.pop(key)
            with open(filename + '.meta', 'w') as output:
                json.dump(metadata, output, indent=2)
        self.stash.delete_file(row['hash'])
        self.search_result.pop(index)
        for listbox in self.listboxes.values():
            listbox.delete(index)
        self.status.set('file removed.')

    def metadata(self):
        self.status.set('Edit Metadata.')
        if self.selected is None:
            showerror('Edit Metadata', 'Please select a file.')
            return
        index = self.selected
        metadata = OrderedDict(self.search_result[index])
        dialog = MetadataEditor(self.window, metadata, self.stash.keywords,
                                    'Edit Metadata')
        if dialog.result is None:
            self.status.set('Editing cancelled.')
            self.window.after(1000, self.clear_status)
            return
        metadata.update(dialog.result)
        self.search_result[index] = metadata
        self.stash.set_fields(metadata)
        for column in self.listboxes.keys():
            listbox = self.listboxes[column]
            listbox.delete(index)
            listbox.insert(index, dialog.result[column])
            listbox.itemconfig(index, bg=selected_bg)
        self.status.set('')

    def configure(self):
        self.status.set('Configure Stash.')
        dialog = FieldEditor(self.window, self.stash,
            title='Manage Metadata')
        add, delete = dialog.result
        for name, type in add:
            name = name.replace('"','')
            self.stash.add_field(name, type)
            if type != 'keyword':
                self.columns.append(name)
                self.add_pane(name)
            else:
                self.update_keyword_menu()
        for name, type in delete:
            self.stash.delete_field(Field((None, name, type)))
            if type != 'keyword':
                if len(self.panes) == 1:
                    raise RuntimeError('Cannot delete last pane')
                pane = self.panes.pop(name)
                self.mainlist.forget(pane)
            else:
                self.update_keyword_menu()
        self.status.set('')

class RemoveQuestion(Dialog):
    def __init__(self, master, row, title=None):
        self.row = row
        Dialog.__init__(self, master, title)

    def body(self, master):
        self.export=tk.BooleanVar(master)
        self.export.set(True)
        self.save_meta=tk.BooleanVar(master)
        frame = ttk.Frame(master)#, borderwidth=2, relief=tk.SUNKEN)
        for key in self.row.keys():
            if key.startswith('_'):
                continue
            ttk.Label(frame, text='%s: %s'%(key, self.row[key])
                     ).pack(ipadx=20, anchor=tk.W)
        frame.pack(padx=20, pady=20, fill=tk.X, expand=1)
        tk.Checkbutton(master,
                       text='Export this file before removing it?',
                       variable=self.export
                       ).pack(padx=20, ipadx=20, anchor=tk.W)
        tk.Checkbutton(master,
            text='Save the metadata for this file?',
                       variable=self.save_meta
                       ).pack(padx=20, ipadx=20, anchor=tk.W)

    def apply(self):
        self.result = {'export first' : self.export.get(),
                       'save metadata': self.save_meta.get()} 

class MetadataEditor(Dialog):
    def __init__(self, parent, metadata, keywords=[],
                     title=None):
        self.metadata = metadata
        self.keywords = keywords
        self.entries = OrderedDict()
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        body = ttk.Frame(self)
        self.initial_focus = self.body(body)
        body.pack(padx=5, pady=5)
        self.buttonbox()
        self.grab_set()
        if not self.initial_focus:
            self.initial_focus = self
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.geometry("+0+0")
        self.initial_focus.focus_set()
        self.wait_window(self)
        
    def body(self, parent):
        R=0
        parent.pack_configure(fill=tk.X, expand=1)
        parent.grid_rowconfigure(0, weight=1)
        fields = [key for key in self.metadata.keys()
                      if key[0] != '_' and key != 'keywords']
        for field in fields:
            tk.Label(parent, text=field + ': ').grid(
                row=R, column=0, sticky=tk.E)
            self.entries[field] = entry = ttk.Entry(parent, width=40)
            entry.insert(0,self.metadata[field] or '')
            if field in ('hash', 'timestamp'):
               entry.config(state='readonly')
            entry.grid(row=R, column=1, sticky=tk.EW)
            R += 1
        keyword_frame = ttk.Frame(parent)
        self.keyword_check_vars = {}
        keyword_set = self.metadata.get('keywords', [])
        for keyword in self.keywords:
            var = tk.IntVar(parent, int(keyword in keyword_set))
            check = tk.Checkbutton(keyword_frame, text=keyword, variable=var)
            self.keyword_check_vars[keyword] = var
            check.pack(anchor=tk.W)
        tk.Label(parent, text='Keywords: ').grid(row=R,column=0, sticky=tk.NE)
        keyword_frame.grid(row=R, column=1, sticky=tk.W)
        self.after(500, self.entries[fields[0]].focus_force)
        
    def apply(self):
        self.result = OrderedDict()
        for key in self.entries:
            if key != 'hash':
                self.result[key] = self.entries[key].get()
        keywords = []
        for keyword in self.keyword_check_vars:
            if self.keyword_check_vars[keyword].get():
                keywords.append(keyword)
        self.result['keywords'] = keywords

    def cancel(self):
        self.parent.deiconify()
        self.parent.focus_set()
        self.destroy()

class NewField(Dialog):

    def body(self, parent):
        self.name_var = name_var = tk.StringVar(parent)
        self.name_entry = name_entry = ttk.Entry(parent, textvariable=name_var)
        self.type_var = type_var = tk.StringVar(parent)
        type_var.set('text')
        type_choice = tk.OptionMenu(
            parent, type_var, 'text', 'integer', 'date', 'keyword')
        type_choice.config(width=15, state=tk.NORMAL)
        ttk.Label(parent, text='Name:').grid(row=0, column=0, sticky=tk.E)
        name_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        ttk.Label(parent, text='Type:').grid(row=1, column=0, sticky=tk.E)
        type_choice.grid(row=1, column=1, sticky=tk.W)
        self.after(500, name_entry.focus_force)

    def check_name(self, *args, **kwargs):
        if self.validate():
            self.SAVE.config(state=tk.NORMAL)
        else:
            self.SAVE.config(state=tk.DISABLED)

    def validate(self):
        name = self.name_var.get()
        if name and name.find(' ') == -1:
            self.result = (name, self.type_var.get())
            return True
        return False
        
    def buttonbox(self):
        box = ttk.Frame(self)
        self.SAVE = SAVE = ttk.Button(box, text="Add Field", width=10,
            command=self.ok, default=tk.ACTIVE)
        self.SAVE.pack(side=tk.LEFT, padx=5, pady=5)
        self.CANCEL = ttk.Button(box, text="Cancel", width=10,
                                command=self.cancel)
        self.CANCEL.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind('<Escape>', self.cancel)
        self.bind('<Return>', self.ok)
        box.pack()
        self.name_var.trace_add('write', self.check_name,)
    
class FieldEditor(Dialog):

    def __init__(self, parent, stash, title=None):
        fields = stash.fields + [
            Field((None, kw, 'keyword')) for kw in stash.keywords]
        self.fields = sorted(fields, key=lambda f: f.name)
        Dialog.__init__(self, parent, title)

    def body(self, parent):
        #self.resizable(width=True, height=False)
        parent.pack_configure(fill=tk.BOTH, expand=1)
        parent.grid_rowconfigure(0, weight=1)
        for n in range(4):
            parent.grid_columnconfigure(n, weight=1)
        self.scrollbar = scrollbar = Scrollbar(parent)
        self.keylist = keylist = tk.Listbox(parent, selectmode='browse',
            activestyle=tk.NONE)
        keylist.bind('<Button-1>', self.select_row)
        self.typelist = typelist = tk.Listbox(parent, selectmode='browse',
            activestyle=tk.NONE)
        typelist.bind('<Button-1>', self.select_row)
        for field in self.fields:
            keylist.insert(tk.END, field.name)
            typelist.insert(tk.END, field.type)
        keylist.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)
        typelist.grid(row=0, column=2, columnspan=2, sticky=tk.NSEW)
        scrollbar.config(command=self.yview)
        keylist.config(yscrollcommand=lambda lo, hi: self.sb_set(keylist,
                        lo, hi))
        typelist.config(yscrollcommand=lambda lo, hi: self.sb_set(typelist,
                        lo, hi))
        scrollbar.grid(row=0, column=4, sticky=tk.NS)
        plusminus = ttk.Frame(parent)
        ttk.Button(plusminus, style='Toolbutton', text='+',
            padding=(5, 0), command=self.add_field).grid(row=0, column=0)
        ttk.Button(plusminus, style='Toolbutton', text='-',
            padding=(5, 0), command=self.delete_field).grid(row=0, column=1)
        plusminus.grid(row=1, column=0, sticky=tk.W)
        #self.cancelled = True
        self.selected = None
        self.result = [], []

    # By default, when a listview becomes inactive the rows all show
    # as unselected.  Only one of our listboxes can be active.  So we
    # set the background color of the selected item in the inactive
    # listview.

    def clear(self):
        for column in self.keylist, self.typelist:
            column.selection_clear(0, tk.END)
            for i in range(len(self.fields) - 2):
                column.itemconfig(i, bg='')
            
    def select(self, column, index):
        for i in range(len(self.fields) - 2):
            column.itemconfig(i, bg='')
        column.selection_clear(0, tk.END)
        column.selection_set(index)
        column.activate(index)
        column.itemconfig(index, bg=selected_bg)

    def select_row(self, event):
        widget = event.widget
        mouse = '@%s,%s'%(event.x, event.y)
        index = widget.index(mouse)
        if index < 0:
            return
        x, y, width, height = widget.bbox(mouse)
        if event.y < y or event.y > y + height:
            self.clear()
            return 'break'
        for i in range(len(self.fields) - 2):
            if i != index:
                widget.itemconfig(i, bg='')
        other = self.keylist if widget == self.typelist else self.typelist
        self.select(other, index)
        self.selected = index

    def buttonbox(self):
        box = ttk.Frame(self)
        self.OK = ttk.Button(box, text="OK", width=10,
                            command=self.ok, default=tk.ACTIVE)
        self.OK.pack(side=tk.LEFT, padx=5, pady=5)
        self.Cancel = ttk.Button(box, text="Cancel", width=10,
                                command=self.cancel)
        self.Cancel.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind('<Escape>', self.cancel)
        self.bind('<Return>', self.add_field)
        box.pack()

    def sb_set(self, widget, lo, hi):
        newtop = widget.nearest(0)
        self.keylist.yview(newtop)
        self.typelist.yview(newtop)
        self.scrollbar.set(lo, hi)

    def yview(self, scroll, number, units=None):
        self.keylist.yview(scroll, number, units)
        self.typelist.yview(scroll, number, units)

    def add_field(self, event=None):
        try:
            name, type = NewField(self).result
        except TypeError:
            return
        self.result[0].append((name, type))
        self.keylist.insert(tk.END, name)
        self.typelist.insert(tk.END, type)

    def delete_field(self, event=None):
        if self.selected is None:
            return
        try:
            name = self.keylist.get(self.selected)
            type = self.typelist.get(self.selected)
        except tk.TclError:
            return
        self.result[1].append((name, type))
        self.keylist.delete(self.selected)
        self.typelist.delete(self.selected)
        
    def apply(self):
        self.cancelled = False
        return self.result

# Menu shortcuts

OSX_shortcuts = {'Open'   : u'\t\t\u2318O',
                 'New'    : u'\t\t\u2318N',
                 'SaveAs' : u'\t\u2318\u21e7S',
                 'Quit'   : u'\t\t   \u2318Q',
                 'Cut'    : u'\t\t\u2318X',
                 'Copy'   : u'\t\u2318C',
                 'Paste'  : u'\t\u2318V'}

Linux_shortcuts = {'Open'   : '',
                   'New'    : '',
                   'SaveAs' : '',
                   'Quit'   : '',
                   'Cut'    : '     Cntl+X',
                   'Copy'   : '',
                   'Paste'  : '  Cntl+V'}

if sys.platform == 'darwin' :
    scut = OSX_shortcuts
elif sys.platform == 'linux2' :
    scut = Linux_shortcuts
else: # fall back choice
    scut = Linux_shortcuts

startup_stashes = []

class StashApp:
    def __init__(self):
        self.curdir = os.path.expanduser('~')
        self.viewers = []
        self.root = root = tk.Tk(className='stash')
        if tk.TkVersion >= 9.0:
            root.wm_attributes(stylemask=('titled', 'fullsizecontent'))
        root.title('Stash')
        _, state = self.get_app_state()
        recents = state.get('recents', [])
        self.recent_dirs = dict((os.path.basename(s), s) for s in recents)
        frame = ttk.Frame(root, width=200, height=200)
        recent_frame = ttk.LabelFrame(frame, text='Recent Stashes')
        self.recent_list = tk.Listbox(recent_frame, height=5, borderwidth=0)
        for stash_dir in self.recent_dirs:
            name = os.path.basename(stash_dir)
            self.recent_list.insert('end', name)
        self.recent_list.bind('<ButtonRelease-1>', self.handle_recent)
        self.recent_list.grid(row=0, column=0, padx=10, pady=10)
        self.browse_button = ttk.Button(recent_frame,
            text='Browse ...',
            command = self.open)
        self.browse_button.grid(row=1, column=0, sticky='s')
        recent_frame.pack()
        frame.pack(padx=20, pady=20)
        if sys.platform != 'darwin':
            root.option_add('*tearOff', tk.FALSE)
            root.tk.call('namespace', 'import', '::tk::dialog::file::')
            root.tk.call('set', '::tk::dialog::file::showHiddenBtn',  '1')
            root.tk.call('set', '::tk::dialog::file::showHiddenVar',  '0')
        root.protocol("WM_DELETE_WINDOW", self.quit)
        menubar = tk.Menu(self.root)
        Application_menu = tk.Menu(menubar, name="apple")
        menubar.add_cascade(label='Stash', menu=Application_menu)
        File_menu = tk.Menu(menubar, name="file")
        menubar.add_cascade(label='File', menu=File_menu)
        Window_menu = tk.Menu(menubar, name='window')
        menubar.add_cascade(label='Window', menu=Window_menu)
        Help_menu = tk.Menu(menubar, name="help")
        menubar.add_cascade(label='Help', menu=Help_menu)
        Application_menu.insert_command(0, label='About Stash ...',
            command=self.about)
        Application_menu.insert_separator(0)
        File_menu.add_command(label='Open...'+scut['Open'],
                              command=self.open)
        File_menu.add_command(label='New...'+scut['New'], command=self.new)
        if sys.platform != 'darwin':
            Application_menu.add_command(label='Quit Stash'+scut['Quit'],
                                             command=self.quit)
            Help_menu.add_command(label='Stash Help', command=self.help)
        root.config(menu=menubar)
        root.focus_force()
#        self.startup_flag = False

    def handle_recent(self, event):
        stash_dir = self.recent_dirs[self.recent_list.selection_get()]
        self.launch_viewer(stash_dir)

    # def startup_launch(self):
    #     for stash in startup_stashes:
    #         self.launch_viewer(stash)
    #     self.startup_flag = True

    def about(self):
        showinfo(title='About Stash',
                 message=u"""
This is version %s of Stash, copyright \u00a9 2010-2023 by Marc Culler.

Stash is distributed under the GNU Public License, version 3 or higher.
 
Stash is written in python, using the SQLite file-based database and \
the Tk toolkit.

To download Stash visit the github page:
https://github.com/culler/stash"""%__version__)

    def quit(self):
        for viewer in [x for x in self.viewers]:
            viewer.close()
        self.root.destroy()

    def open(self):
        _, state = self.get_app_state()
        initial_dir = state.get('parent_dir', self.curdir)
        directory = askdirectory(mustexist=True,
                                 title='Choose a stash',
                                 initialdir=initial_dir)
        if directory is None or directory == '':
            return
        state['parent_dir'] = os.path.dirname(directory)
        recents = state.get('recents', [])
        try:
            recents.remove(directory)
        except ValueError:
            pass
        recents.insert(0, directory)
        state['recents'] = recents[:5]
        self.save_app_state(state)
        self.launch_viewer(directory)
        self.curdir = os.path.dirname(directory)

    def launch_viewer(self, directory):
        try:
            viewer = StashViewer(self, directory)
        except StashError as E:
            showerror('Open Stash', E.value)
            return
        self.viewers.append(viewer)
        self.root.withdraw()
            
    def close_viewer(self, stash):
        try:
            index = self.viewers.index(stash)
            self.viewers.remove(stash)
        except ValueError:
            pass
        if len(self.viewers) == 0:
            #### Need to update the recent dirs before closing the last viewer
            self.root.deiconify()
            self.root.update_idletasks()
            self.root.focus_force()

    def new(self):
        newstash = asksaveasfilename(
            title='Choose a name and location for your stash.')
        if newstash == None or newstash == '':
            return
        temp = Stash()
        dialog = FieldEditor(self.root, temp,
                           title='Create Metadata Fields')
        if not dialog.result:
            return
        try:
            temp.create(newstash)
        except StashError as E:
            showerror('Create New Stash', E.value)
        for name, type in dialog.result[0]:
            temp.add_field(name, type)
        temp.close()
        self.curdir = os.path.dirname(newstash)
        self.launch_viewer(newstash)

    def help(self):
        browser.open_new_tab('file://' + pathname2url(stash_doc_path))

        # def enable_apple_events(self):
        # if sys.platform == 'darwin':
        #     def open_file(*args):
        #         for arg in args:
        #             dirname, filename = os.path.split(arg)
        #             if filename == 'db.stash':
        #                 startup_stashes.append(dirname)
        #         self.startup_launch()
        #     self.root.createcommand("::tk::mac::OpenDocument", open_file)

    #### Need to add equivalent for other platforms ####
    def _get_app_support_dir(self):
        home = os.environ.get('HOME', None)
        if home is None:
            return None
        if sys.platform == 'darwin':
           return os.path.join(
               home, 'Library', 'Application Support', 'Stash')

    def get_app_state(self):
        app_support_dir = self._get_app_support_dir()
        if app_support_dir is None:
            return None, {}
        os.makedirs(app_support_dir, exist_ok=True)
        state_file = os.path.join(app_support_dir, 'state.plist')
        if os.path.exists(state_file):
            try:
                with open(state_file, 'rb') as plist_file:
                    state = plistlib.load(plist_file)
                return state_file, state
            except plistlib.InvalidFileException:
                os.unlink(state_file)
        return state_file, {}

    def save_app_state(self, state_dict):
        state_file, state = self.get_app_state()
        if state_file is None:
            return
        state.update(state_dict)
        with open(state_file, 'wb') as plist_file:
            plistlib.dump(state, plist_file)

    def run(self):
        self.root.mainloop()
        
def main():
    app = StashApp()
    app.run()
    
if __name__ == '__main__':
    main()
