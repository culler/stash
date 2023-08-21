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

import os, sys, time
from collections import OrderedDict
import webbrowser
from .stash import Stash, StashError, __file__ as stashfile
from . import __version__
import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
from tkinter.messagebox import showerror, showwarning, showinfo
from tkinter.simpledialog import Dialog
from urllib.request import pathname2url
import threading
from .theme import StashStyle

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
    # (Binding to mouse wheel events is currently broken in OS X.) 
    def yscroll(self, lo, hi):
        self.viewer.scrollbar_set(self, lo, hi)

class StashViewer():
    def __init__(self, app, directory):
        self.app = app
        self.stash_dir = directory
        self.curdir = directory
        self.stash_name = os.path.basename(directory)
        self.stash = Stash()
        self.stash.open(directory)
        fields = self.stash.fields
        self.columns = columns = [x.name for x in fields]
        self.selected = set()
        self.root = root = tk.Toplevel(app.root, class_='stash')
        self.style = StashStyle(root)
        windowbg=self.style.WindowBG
        prefs = self.stash.get_preference('geometry')
        if prefs:
            self.root.geometry(prefs[0]['value'])
        else:
            root.geometry('+200+80')
        root.title(self.stash_name)
        root.protocol("WM_DELETE_WINDOW", self.close)
        root.grid_columnconfigure(0, weight=1)
        root.grid_rowconfigure(1, weight=1)
        topframe = tk.Frame(root,
                             relief=tk.FLAT,
                             borderwidth=10,
                             background=windowbg)
        topframe.grid(row=0, columnspan=2, sticky=tk.EW)
        gobutton = ttk.Button(topframe,
                             text='Show Files',
                             command=self.match)
        gobutton.grid(row=0, column=0, sticky=tk.W+tk.S, padx=2)
        searchlabel = tk.Label(topframe, text='with: ', bg=windowbg)
        searchlabel.grid(row=0, column=1, sticky=tk.E)
        dummy_var = tk.StringVar(root)
        keyword_button = tk.OptionMenu(topframe, variable=dummy_var, value='Keywords')
        dummy_var.set('Keywords')
        keyword_menu = keyword_button['menu']
        keyword_menu.delete(0)
        self.keyword_vars = {}
        for keyword in self.stash.keywords:
            var = tk.IntVar(root)
            keyword_menu.add_checkbutton(label=keyword, onvalue=1, offvalue=0,
                                             variable=var)
            self.keyword_vars[keyword] = var
        keyword_button.grid(row=0, column=2, sticky=tk.W, ipady=2)        
        columns = self.columns
        self.order_var = order_var = tk.StringVar(root)
        if len(columns) > 0:
            order_var.set(columns[0])
            self.ordermenu = ordermenu = ttk.OptionMenu(topframe,
                                                       order_var,
                                                       *columns)
            label = tk.Label(topframe, text="Sort by: ", background=windowbg)
            label.grid(row=0, column=3, sticky=tk.E)
            ordermenu.grid(row=0, column=4)
            self.desc_var = desc_var = tk.BooleanVar(root)
            desc_var.set(False)
            self.descend = descend = tk.Checkbutton(topframe,
                                                    text="Desc",
                                                    variable=desc_var,
                                                    background=windowbg,
                                                    highlightthickness=0)
            descend.grid(row=0, column=5)
        topframe.grid_columnconfigure(3, weight=1)
        self.mainlist = mainlist = tk.PanedWindow(root,
                                                  borderwidth=0,
                                                  sashpad=0,
                                                  sashwidth=8,
                                                  handlesize=8,
                                                  handlepad=6,
                                                  showhandle=True,
                                                  sashrelief=tk.RAISED,
                                                  relief=tk.FLAT)
        self.scrollbar = scrollbar = Scrollbar(root)
        self.listboxes = {}
        self.filters = {}
        self.bgcolor = ['white','#f0f5ff']
        for column in self.columns:
            self.add_pane(column)
        scrollbar.config(command=self.yview)
        mainlist.grid(row=1, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=1, column=1, sticky=tk.NS)
        spacer = tk.Frame(root, background=windowbg, height=2, borderwidth=0,
                 relief=tk.FLAT)
        spacer.grid(row=2, columnspan=2, sticky=tk.EW)
        self.status = status = tk.StringVar(self.root)
        statusbox = tk.Entry(self.root,
                             state=tk.DISABLED,
                             disabledforeground='red',
                             textvariable=status,
                             relief=tk.FLAT)
        statusbox.grid(row=3, column=0, sticky=tk.EW, padx=20)
        self.menubar = menubar = tk.Menu(root)
        menubar = tk.Menu(self.root)
        Application_menu = tk.Menu(menubar, name="apple")
        menubar.add_cascade(label='Stash', menu=Application_menu)
        File_menu = tk.Menu(menubar, name="file")
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
        Action_menu.add_command(label='Export...', command=self.export_files)
        Action_menu.add_command(label='Remove...', command=self.remove_files)
        Action_menu.add_command(label='Metadata...', command=self.metadata)
        Action_menu.add_command(label='Configure...', command=self.configure)
        Help_menu = tk.Menu(menubar, name="help")
        menubar.add_cascade(label='Help', menu=Help_menu)
        if sys.platform != 'darwin':
            Application_menu.add_command(label='Quit Stash'+scut['Quit'],
                command=self.app.quit)
            Help_menu.add_command(label='Stash Help', command=self.app.help)
        root.config(menu=menubar)
        self.set_sashes()
        root.bind("<Return>", self.match)
        root.update_idletasks()
        
    def add_pane(self, column):
        # needs a minimum size if the lists are empty
        pane = tk.PanedWindow(self.mainlist,
                              orient=tk.VERTICAL,
                              borderwidth=0,
                              background='white')
        label = tk.Label(pane, text=column,
                         background=self.style.WindowBG,
                         relief=tk.RAISED,
                         borderwidth=1)
        filter = ttk.Entry(pane)
        listbox = Listbox(pane, height=10, borderwidth=0,
                          activestyle=tk.NONE,
                          selectmode=tk.SINGLE,
                          relief=tk.FLAT,
                          background='white')
        listbox.viewer = self
        listbox.config(yscrollcommand = listbox.yscroll)
        listbox.bind('<Button-1>', self.uniselect)
        listbox.bind('<Shift-Button-1>', self.multiselect)
        listbox.bind('<Double-Button-1>', self.double_click)
        self.listboxes[column] = listbox
        self.filters[column] = filter
        pane.rowconfigure(2, weight=1)
        pane.columnconfigure(0, weight=1)
        label.grid(row=0, column=0, sticky=tk.EW)
        filter.grid(row=1, column=0, sticky=tk.EW)
        listbox.grid(row=2, column=0, sticky=tk.NSEW)
        self.mainlist.add(pane)
        self.mainlist.paneconfigure(pane, padx=0, pady=0)

    def set_sashes(self):
        pref = self.stash.get_preference('sashes')
        try:
            pref_value = pref[0]['value']
        except IndexError:
            return
        if pref_value:
            coords = pref_value.split(':')
            for N in range(len(coords) - 1, -1, -1):
                self.root.update()
                try:
                    self.mainlist.sash_place(N, coords[N], 0)
                except tk.TclError:
                    pass

    def activate(self):
        self.root.deiconify()
        self.root.focus_force()

    def close(self):
        self.stash.set_preference('geometry', self.root.geometry())
        sashes = [str(self.mainlist.sash_coord(N)[0])
                  for N in range(len(self.columns) - 1)]
        self.stash.set_preference('sashes', ':'.join(sashes))
        self.stash.close()
        self.app.checkout(self)
        self.root.destroy()

    def scrollbar_set(self, widget, lo, hi):
        newtop = widget.nearest(0)
        for listbox in self.listboxes.values():
            listbox.yview(newtop)
        self.scrollbar.set(lo, hi)

    def yview(self, scroll, number, units=None):
        for listbox in self.listboxes.values():
            listbox.yview(scroll, number, units)

    def toggle(self, index):
        if index in self.selected:
            self.selected.remove(index)
            color=self.bgcolor[index%2]
        else:
            self.selected.add(index)
            color='lightblue'
        for listbox in self.listboxes.values():
            listbox.itemconfig(index, bg=color)

    def clear(self):
        for listbox in self.listboxes.values():
            for index in self.selected:
                try:
                    listbox.itemconfig(index, bg=self.bgcolor[index%2])
                except TclError:
                    pass
        self.selected = set()
        
    def uniselect(self, event):
        index = event.widget.index('@%s,%s'%(event.x, event.y))
        if index > -1:
            self.clear()
            self.toggle(index)
        return 'break'

    def multiselect(self, event):
        index = event.widget.index('@%s,%s'%(event.x, event.y))
        if index > -1:
            self.toggle(index)
        return 'break'

    def double_click(self, event):
        self.uniselect(event)
        if len(self.selected) > 0:
            for index in self.selected:
                self.stash.view_file(self.search_result[index]['hash'])
        return 'break'

    def display_results(self):
        self.selected = []
        for column in self.columns:
            self.listboxes[column].delete(0,tk.END)
        count = 0
        for row in self.search_result:
            for column in self.columns:
                box = self.listboxes[column]
                box.insert(tk.END, row[column] or '')
                box.itemconfig(count, background=self.bgcolor[count%2])
            count += 1
        self.status.set('%d file%s found.'%(count, '' if count==1 else 's'))

    def match_clause(self):
        booleans = []
        columns = self.stash.fields
        keys = [column.name for column in columns]
        first = self.order_var.get()
        if first in keys:
            keys.remove(first)
            keys.insert(0, first)
        keys = ["`%s`"%key for key in keys]
        if self.desc_var.get():
            keys[0] = keys[0] + ' desc'
        if keys:
            orderby = ' order by ' + ', '.join(keys)
        else:
            orderby = ''
#        if len(terms) == 0:
#            return '1' + orderby
#        for term in terms:
#            for column in columns:
#                booleans.append("%s like '%%%s%%'"%(column.name, term))
#        return ' or '.join(booleans) + orderby
        for column in self.columns:
            filter = self.filters[column].get()
            if not filter:
                continue
            terms = filter.split()
            for term in terms:
                booleans.append("%s like '%%%s%%'"%(column, term))
        if not booleans:
            return '1' + orderby
        else:
            return ' and '.join(booleans) + orderby

    def match(self, event=None):
        where = self.match_clause()
        self.search_result = self.stash.find_files(where)
        self.display_results()

    def clear_status(self):
        self.status.set('')

    def import_file(self):# Could accept many files?
        self.status.set('Import file.')
        filename = askopenfilename(parent=self.root,
                                   title='Choose a file to import',
                                   initialdir=self.stash_dir)
        if filename is None or filename=='':
            self.status.set('Import cancelled.')
            self.root.after(1000, self.clear_status)
            return
        if not os.path.isfile(filename):
            showerror('Import File', '%s is not a file.'%filename)
        self.curdir = os.path.dirname(filename)
        webbrowser.open_new_tab('file://%s'%filename)
        metadata = OrderedDict([(x, '') for x in self.columns])
        dialog = MetadataEditor(self.root, metadata, 'Create Metadata', hide_main=True)
        if dialog.result is None:
            self.status.set('Import cancelled')
            self.root.after(1000, self.clear_status)
            return
        try:
            self.stash.insert_file(filename, dialog.result)
        except StashError as E:
            showerror('Import File', E.value)
        self.matchbox.focus_set()
        self.status.set('')

    def export_files(self):
        self.status.set('Export files.')
        if len(self.selected) == 0:
            showerror('Export Files', 'Please select some files.')
            return
        for index in self.selected:
            row = self.search_result[index]
            self.export_one_file(row)
        self.status.set('')

    def export_one_file(self, row):
        default_filename = row['filename']
        default_extension = os.path.splitext(default_filename)[1]
        filename = asksaveasfilename(parent=self.root,
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

    def remove_files(self):
        self.status.set('Remove files.')
        count = 0
        if len(self.selected) == 0:
            showerror('Remove Files', 'Please select some files.')
            return
        selected = list(self.selected)
        while len(selected) > 0:
            index = selected.pop()
            self.selected.remove(index)
            row = self.search_result[index]
            dialog = RemoveQuestion(self.root, row, title='Remove File')
            if dialog.result is None:
                self.status.set('Removal cancelled.')
                self.root.after(1000, self.clear_status)
                return
            if dialog.result['export first']:
                filename = self.export_one_file(row)
                if filename is None:
                    return
            if dialog.result['save metadata']:
                meta_file = open(filename + '.meta', 'w')
                meta_file.write('{\n')
                for key in row.keys():
                    if key in ('hash', 'filename', 'timestamp'):
                        continue
                    meta_file.write(" '%s' : '%s'\n"%(key, row[key]))
                meta_file.write('}\n')
                meta_file.close()
            self.stash.delete_file(row['hash'])
            count += 1
            self.search_result.pop(index)
            for listbox in self.listboxes.values():
                listbox.delete(index)
        self.status.set('%s file%s removed.'%(count, '' if count==1 else 's'))

    def metadata(self):
        self.status.set('Edit Metadata.')
        if len(self.selected) == 0:
            showerror('Edit Metadata', 'Please select some files.')
            return
        for index in self.selected:
            metadata = OrderedDict(self.search_result[index])
            dialog = MetadataEditor(self.root, metadata, 'Edit Metadata')
            if dialog.result is None:
                self.status.set('Editing cancelled.')
                self.root.after(1000, self.clear_status)
                continue
            self.stash.set_fields(dialog.result, metadata['hash'])
            metadata.update(dialog.result)
            self.search_result[index] = metadata
            for column in self.listboxes.keys():
                listbox = self.listboxes[column]
                listbox.delete(index)
                listbox.insert(index, dialog.result[column])
                listbox.itemconfig(index, bg='lightblue')
        self.status.set('')

    def configure(self):
        self.status.set('Configure Stash.')
        dialog = FieldEditor(self.root,
                           self.stash.fields,
                           title='Manage Metadata')
        for key, type in dialog.result:
            key = key.replace('"','')
            self.stash.add_field(key, type)
            self.columns.append(key)
            self.add_pane(key)
        self.status.set('')
        return dialog.result

class RemoveQuestion(Dialog):
    def __init__(self, master, row, title=None):
        self.row = row
        Dialog.__init__(self, master, title)

    def body(self, master):
        self.export=tk.BooleanVar(master)
        self.export.set(True)
        self.save_meta=tk.BooleanVar(master)
        frame = tk.Frame(master, borderwidth=2, relief=tk.SUNKEN)
        for key in self.row.keys():
            tk.Label(frame, text='%s: %s'%(key, self.row[key])
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
    def __init__(self, parent, metadata, title=None, hide_main=False):
        self.metadata = metadata
        self.entries = OrderedDict()
        tk.Toplevel.__init__(self, parent)
        if hide_main:
            parent.withdraw()
        else:
            self.transient(parent)
        if title:
            self.title(title)
        self.parent = parent
        self.result = None
        body = tk.Frame(self)
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
        
    def body(self, master):
        R=0
        master.pack_configure(fill=tk.X, expand=1)
        master.grid_rowconfigure(0, weight=1)
        keys = self.metadata.keys()
        for key in keys:
            tk.Label(master, text=key+': ').grid(row=R,column=0, sticky=tk.E)
            self.entries[key] = entry = tk.Entry(master, width=40)
            entry.insert(0,self.metadata[key] or '')
            if key in ('hash', 'timestamp'):
               entry.config(state='readonly') 
            entry.grid(row=R, column=1, sticky=tk.EW)
            R += 1
        for key in keys:
            self.entries[key].focus_set()
            break
        
    def apply(self):
        self.result = OrderedDict()
        for key in self.entries:
            if key != 'hash':
                self.result[key] = self.entries[key].get()

    def cancel(self):
        self.parent.deiconify()
        self.parent.focus_set()
        self.destroy()

class NewField(Dialog):

    def body(self, parent):
        self.name_var = name_var = tk.StringVar(parent)
        self.name_entry = name_entry = tk.Entry(parent, textvariable=name_var)
        self.type_var = type_var = tk.StringVar(parent)
        type_var.set('text')
        type_choice = tk.OptionMenu(
            parent, type_var, 'text', 'integer', 'date', 'keyword')
        type_choice.config(width=15, state=tk.NORMAL)
        ttk.Label(parent, text='Name:').grid(row=0, column=0, sticky=tk.E)
        name_entry.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        ttk.Label(parent, text='Type:').grid(row=1, column=0, sticky=tk.E)
        type_choice.grid(row=1, column=1, sticky=tk.W)

    def check_name(self, *args, **kwargs):
        if self.validate():
            self.SAVE.config(state=tk.NORMAL)
        else:
            self.SAVE.config(state=tk.DISABLED)

    def validate(self):
        name = self.name_var.get()
        if name and name.find(' ') == -1:
            return True
        return False
        
    def ok(self, event=None):
        self.result = (self.name_var.get(), self.type_var.get())
        return super().ok(event)

    def buttonbox(self):
        box = tk.Frame(self)
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

    def __init__(self, parent, fields, title=None, new=False):
        self.fields = fields
        self.new = new
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
        keylist.config(yscrollcommand=lambda lo, hi: self.sb_set(keylist, lo, hi))
        typelist.config(yscrollcommand=lambda lo, hi: self.sb_set(typelist, lo, hi))
        scrollbar.grid(row=0, column=4, sticky=tk.NS)
        plusminus = ttk.Frame(parent)
        ttk.Button(plusminus, style='Toolbutton', text='+',
            padding=(5, 0), command=self.add_field).grid(row=0, column=0)
        ttk.Button(plusminus, style='Toolbutton', text='-',
            padding=(5, 0), command=self.delete_field).grid(row=0, column=1)
        plusminus.grid(row=1, column=0, sticky=tk.W)
        self.cancelled = True
        self.result = []

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
        #column.selection_anchor(index)
        column.itemconfig(index, bg='systemSelectedTextBackgroundColor')

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

    def buttonbox(self):
        box = tk.Frame(self)
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
        key, type = NewField(self).result
        self.result.append( (key, type) )
        self.keylist.insert(tk.END, key)
        self.typelist.insert(tk.END, type)

    def delete_field(self, event=None):
        print('delete', self.keyentry.get(), self.type_var.get())
        
    def validate(self):
        if self.new and len(self.result) == 0:
            return False
        else:
            return True

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
        root.title('Stash')
        if sys.platform == 'darwin':
            self.enable_apple_events()
            root.withdraw()
        else:
            root.option_add('*tearOff', tk.FALSE)
            root.geometry('300x0+100+10')
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
            Application_menu.add_command(label='Quit Stash'+scut['Quit'], command=self.quit)
            Help_menu.add_command(label='Stash Help', command=self.help)
        root.config(menu=menubar)
        self.startup_flag = False

    def startup_launch(self):
        for stash in startup_stashes:
            self.launch_viewer(stash)
        self.startup_flag = True

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
        directory = askdirectory(mustexist=True,
                                 title='Choose a stash',
                                 initialdir=self.curdir)
        if directory is None or directory == '':
            return
        else:
            self.launch_viewer(directory)
            self.curdir = os.path.dirname(directory)

    def launch_viewer(self, directory):
        try:
            viewer = StashViewer(self, directory)
        except StashError as E:
            showerror('Open Stash', E.value)
            return
        self.viewers.append(viewer)
            
    def checkout(self, stash):
        try:
            index = self.viewers.index(stash)
            self.viewers.remove(stash)
        except ValueError:
            print(self.viewers)
        if len(self.viewers) == 0:
            if sys.platform != 'darwin':
                self.quit()
            else:
                # This voodoo brings the application menu bar back
                # when the last window closes. Without doing both of
                # these you get a blank menu bar.
                self.root.deiconify()
                self.root.focus_force()
                self.root.withdraw()

    def new(self):
        newstash = asksaveasfilename(
            title='Choose a name and location for your stash.')
        if newstash == None or newstash == '':
            return
        dialog = FieldEditor(self.root,
                           [],
                           title='Create Metadata Fields',
                           new=True)
        if dialog.cancelled:
            return
        temp = Stash()
        try:
            temp.create(newstash)
        except StashError as E:
            showerror('Create New Stash', E.value)
        for key, type in dialog.result:
            temp.add_field(key, type)
        temp.close()
        self.curdir = os.path.dirname(newstash)
        self.launch_viewer(newstash)

    def help(self):
        webbrowser.open_new_tab('file:' + stash_doc_path)

    def enable_apple_events(self):
        def doOpenFile(*args):
            for arg in args:
                dirname, filename = os.path.split(arg)
                if filename == 'db.stash':
                    startup_stashes.append(dirname)
            self.startup_launch()

        self.root.createcommand("::tk::mac::OpenDocument", doOpenFile)

    def run(self):
        self.root.mainloop()
        
def main():
    app = StashApp()
    app.run()
    
if __name__ == '__main__':
    main()
