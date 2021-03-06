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


import os, sys, time
try:
    from collections import OrderedDict
except ImportError:
    from .fod import FakeOrderedDict as OrderedDict
from .stash import Stash, StashError, browser, __file__ as stashfile
from .version import __version__
if sys.version_info.major > 2:
    import tkinter as tk
    from tkinter import ttk
    from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename
    from tkinter.messagebox import showerror, showwarning, showinfo
    from tkinter.simpledialog import Dialog
    from urllib.request import pathname2url
else:
    import Tkinter as tk
    import ttk
    from tkFileDialog import askdirectory, askopenfilename, asksaveasfilename
    from tkMessageBox import showerror, showwarning, showinfo
    from tkSimpleDialog import Dialog
    from urllib import pathname2url
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
            # grid_remove is currently missing from Tkinter!
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
        self.curdir = os.path.expanduser('~')
        self.stash_name = os.path.basename(directory)
        self.stash = Stash()
        self.stash.open(directory)
        search_keys = self.stash.search_keys
        if len(search_keys) > 2:
            self.columns = [x.key for x in search_keys[2:]]
        else:
            self.columns = []
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
                             text='Find',
                             command=self.match)
        gobutton.grid(row=0, column=0, sticky=tk.W+tk.S, padx=2)
        searchlabel = tk.Label(topframe, text='files matching: ', bg=windowbg)
        searchlabel.grid(row=0, column=1, sticky=tk.E)
        self.matchbox = matchbox = tk.Entry(topframe,
                                            highlightbackground=windowbg,
                                            width=30)
        matchbox.grid(row=0, column=2, sticky=tk.W, ipady=2)
        matchbox.focus_set()
        self.root.bind("<Return>", self.match)
        columns = self.columns
        self.order_var = order_var = tk.StringVar(self.root)
        if len(columns) > 0:
            order_var.set(columns[0])
            self.ordermenu = ordermenu = ttk.OptionMenu(topframe,
                                                       order_var,
                                                       *columns)
            label = tk.Label(topframe, text="Sort by: ", background=windowbg)
            label.grid(row=0, column=3, sticky=tk.E)
            ordermenu.grid(row=0, column=4)
            self.desc_var = desc_var = tk.BooleanVar(self.root)
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
        Python_menu = tk.Menu(menubar, name="apple")
        Python_menu.add_command(label='About Stash ...',
                                    command=self.app.about)
        Python_menu.add_separator()
        if sys.platform != 'darwin':
            Python_menu.add_command(label='Quit Stash', command=self.app.quit)
        menubar.add_cascade(label='Stash', menu=Python_menu)
        self.Action_menu = Action_menu = tk.Menu(self.app.menubar, name='action')
        Action_menu.add_command(label='Import...', command=self.import_file)
        Action_menu.add_command(label='Export...', command=self.export_files)
        Action_menu.add_command(label='Remove...', command=self.remove_files)
        Action_menu.add_command(label='Metadata...', command=self.metadata)
        Action_menu.add_command(label='Configure...', command=self.configure)
        menubar.add_cascade(label='File', menu=self.app.File_menu)
        menubar.add_cascade(label='Action', menu=self.Action_menu)
        menubar.add_cascade(label='Window', menu=self.app.Window_menu)
        Help_menu = tk.Menu(menubar, name="help")
        if sys.platform == 'darwin':
            self.app.root.createcommand('::tk::mac::ShowHelp', self.app.help)
        else:
            Help_menu.add_command(label='Stash Help',
                                  command=self.app.help)
        menubar.add_cascade(label='Help', menu=Help_menu)
        root.config(menu=menubar)
        self.set_sashes()

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
        self.listboxes[column]=listbox
        label.pack(fill = tk.X, expand=0, padx=0, pady=0)
        listbox.pack(fill=tk.BOTH, expand=1, padx=5, pady=0,)
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
                self.mainlist.sash_place(N, coords[N], 0)

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
                listbox.itemconfig(index, bg=self.bgcolor[index%2])
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
                box.insert(tk.END, row[column])
                box.itemconfig(count, background=self.bgcolor[count%2])
            count += 1
        self.status.set('%d file%s found.'%(count, '' if count==1 else 's'))

    def match_clause(self, match):
        terms = match.split()
        booleans = []
        columns = self.stash.search_keys[2:]
        keys = [column.key for column in columns]
        first = self.order_var.get()
        if first in keys:
            keys.remove(first)
            keys.insert(0, first)
        keys = ["`%s`"%key for key in keys]
        if self.desc_var.get():
            keys[0] = keys[0] + ' desc'
        orderby = ' order by ' + ', '.join(keys)
        if len(terms) == 0:
            return '1' + orderby
        for term in terms:
            for column in columns:
                booleans.append("%s like '%%%s%%'"%(column.key, term))
        return ' or '.join(booleans) + orderby

    def match(self, event=None):
        where = self.match_clause(self.matchbox.get())
        self.search_result = self.stash.find_files(where)
        self.display_results()

    def clear_status(self):
        self.status.set('')

    def import_file(self):# Could accept many files?
        self.status.set('Import file.')
        filename = askopenfilename(parent=self.root,
                                   title='Choose a file to import',
                                   initialdir=self.curdir)
        if filename is None or filename=='':
            self.status.set('Import cancelled.')
            self.root.after(1000, self.clear_status)
            return
        if not os.path.isfile(filename):
            showerror('Import File', '%s is not a file.'%filename)
        self.curdir = os.path.dirname(filename)
        browser.open_new_tab('file://%s'%filename)
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
                                     initialdir=self.curdir,
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
            self.stash.set_search_keys(dialog.result, metadata['hash'])
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
        dialog = KeyEditor(self.root,
                           self.stash.search_keys,
                           title='Manage Search Keys')
        for key, type in dialog.result:
            key = key.replace('"','')
            self.stash.add_search_key(key, type)
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
            entry.insert(0,self.metadata[key])
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
        
class KeyEditor(Dialog):

    def __init__(self, parent, search_keys, title=None, new=False):
        self.search_keys = search_keys
        self.new = new
        Dialog.__init__(self, parent, title)

    def body(self, master):
        self.resizable(width=True, height=False)
        master.pack_configure(fill=tk.BOTH, expand=1)
        master.grid_rowconfigure(0, weight=1)
        for n in range(4):
            master.grid_columnconfigure(n, weight=1)
        self.scrollbar = scrollbar = Scrollbar(master)
        self.keylist = keylist = tk.Listbox(master, )
        keylist.bind('<Button-1>', lambda event: 'break')
        self.typelist = typelist = tk.Listbox(master)
        typelist.bind('<Button-1>', lambda event: 'break')
        for skey in self.search_keys:
            keylist.insert(tk.END, skey.key)
            typelist.insert(tk.END, skey.type)
        keylist.grid(row=0, column=0, columnspan=2, sticky=tk.NSEW)
        typelist.grid(row=0, column=2, columnspan=2, sticky=tk.NSEW)
        scrollbar.config(command=self.yview)
        keylist.config(yscrollcommand=lambda lo, hi: self.sb_set(keylist, lo, hi))
        typelist.config(yscrollcommand=lambda lo, hi: self.sb_set(typelist, lo, hi))
        scrollbar.grid(row=0, column=4, sticky=tk.NS)
        self.keyentry = keyentry = tk.Entry(master)
        keyentry.grid(row=1, column=0, columnspan=2, sticky=tk.EW)
        self.typevar = typevar = tk.StringVar(master)
        typevar.set('text')
        typechoice = typechoice = tk.OptionMenu(
            master, typevar,
            'text', 'integer', 'date')
        typechoice.grid(row=1, column=2)
        addbutton=tk.Button(master, text='Add', command=self.add_key)
        addbutton.grid(row=1, column=3)
        self.cancelled = True
        self.result = []
        return self.keyentry

    def buttonbox(self):
        box = tk.Frame(self)
        self.OK = tk.Button(box, text="OK", width=10,
                            command=self.ok, default=tk.ACTIVE)
        self.OK.config(state=tk.DISABLED)
        self.OK.pack(side=tk.LEFT, padx=5, pady=5)
        self.Cancel = tk.Button(box, text="Cancel", width=10,
                                command=self.cancel)
        self.Cancel.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind('<Escape>', self.cancel)
        self.bind('<Return>', self.add_key)
        box.pack()

    def sb_set(self, widget, lo, hi):
        newtop = widget.nearest(0)
        self.keylist.yview(newtop)
        self.typelist.yview(newtop)
        self.scrollbar.set(lo, hi)

    def yview(self, scroll, number, units=None):
        self.keylist.yview(scroll, number, units)
        self.typelist.yview(scroll, number, units)

    def add_key(self, event=None):
        key, type = self.keyentry.get(), self.typevar.get()
        self.result.append( (key, type) )
        self.keylist.insert(tk.END, key)
        self.typelist.insert(tk.END, type)
        self.keyentry.delete(0, tk.END)
        self.typevar.set('text')
        self.OK.config(state=tk.NORMAL)

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

class StashApp:
    def __init__(self, args=[]):
        self.curdir = os.path.expanduser('~')
        self.viewers=[]
        self.root = root = tk.Tk(className='stash')
        if sys.platform == 'darwin':
            # Hide the root off the screen.
            root.geometry('0x0+-10+0')
        else:
            root.title('Stash')
            root.option_add('*tearOff', tk.FALSE)
            root.geometry('300x0+100+10')
            root.tk.call('namespace', 'import', '::tk::dialog::file::')
            root.tk.call('set', '::tk::dialog::file::showHiddenBtn',  '1')
            root.tk.call('set', '::tk::dialog::file::showHiddenVar',  '0')
        self.menubar = menubar = tk.Menu(self.root)
        Python_menu = tk.Menu(menubar, name="apple")
        Python_menu.add_command(label='About Stash ...', command=self.about)
        Python_menu.add_separator()
        if sys.platform != 'darwin':
            root.protocol("WM_DELETE_WINDOW", self.quit)
            Python_menu.add_command(label='Quit Stash'+scut['Quit'], command=self.quit)
        menubar.add_cascade(label='Stash', menu=Python_menu)
        self.File_menu = File_menu = tk.Menu(menubar, name="file")
        File_menu.add_command(label='Open...'+scut['Open'],
                              command=self.open)
        File_menu.add_command(label='New...'+scut['New'], command=self.new)
        menubar.add_cascade(label='File', menu=File_menu)
        self.Window_menu = Window_menu = tk.Menu(menubar, name='viewers')
        menubar.add_cascade(label='Window', menu=Window_menu)
        Help_menu = tk.Menu(menubar, name="help")
        if sys.platform == 'darwin':
            root.createcommand('::tk::mac::ShowHelp', self.help)
        else:
            Help_menu.add_command(label='Stash Help',
                                  command=self.help)
        menubar.add_cascade(label='Help', menu=Help_menu)
        root.config(menu=menubar)        
        for directory in args:
            if os.path.isdir(directory):
                self.launch_viewer(directory)

    def about(self):
        showinfo(title='About Stash',
                 message=u"""
This is version %s of Stash, copyright \u00a9 2010-2017 by Marc Culler.

Stash is distributed under the GNU Public License, version 3 or higher.
 
Stash is written in python, using the SQLite file-based database and \
the Tk toolkit.

To download Stash visit the bitbucket page:
https://bitbucket.org/marc_culler/stash"""%__version__)

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
        self.root.withdraw()
        self.Window_menu.add_command(label=viewer.stash_name,
                                         command=viewer.activate)
            
    def checkout(self, stash):
        try:
            index = self.viewers.index(stash)
            self.viewers.remove(stash)
            self.Window_menu.delete(index)
        except IndexError:
            pass
        if len(self.viewers) == 0:
            if sys.platform != 'darwin':
                self.quit()
            else:
                # This voodoo brings the application menu bar back
                # when the last window closes. Without doing both of
                # these you get a blank menu bar.
                self.root.deiconify()
                self.root.focus_force()

    def new(self):
        newstash = asksaveasfilename(
            title='Choose a name and location for your stash.')
        if newstash == None or newstash == '':
            return
        dialog = KeyEditor(self.root,
                           [],
                           title='Create Search Keys',
                           new=True)
        if dialog.cancelled:
            return
        temp = Stash()
        try:
            temp.create(newstash)
        except StashError as E:
            showerror('Create New Stash', E.value)
        for key, type in dialog.result:
            temp.add_search_key(key, type)
        temp.close()
        self.curdir = os.path.dirname(newstash)
        self.launch_viewer(newstash)

    def help(self):
        browser.open_new_tab('file:' + stash_doc_path)

    def run(self):
        self.root.mainloop()

def main():
    app = StashApp(args=sys.argv)
    app.run()
    
if __name__ == '__main__':
    main()
