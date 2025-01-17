# -*- coding: utf-8 -*-
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

from __future__ import unicode_literals
import sys
import tkinter as tk
from tkinter import ttk as ttk
from tkinter.font import Font

class _StashStyle:
    def __init__(self):
        self.ttk_style = ttk_style = ttk.Style()
        if sys.platform == 'darwin':
            self.WindowBG = 'SystemDialogBackgroundActive'
            self.GroupBG = 'SystemSecondaryGroupBoxBackground'
        elif sys.platform == 'win32':
            self.WindowBG = self.GroupBG = 'SystemButtonHighlight'
        else:
            self.WindowBG = self.GroupBG = ttk_style.lookup('TLabelframe', 'background')
        self.font_info = fi = Font(font=ttk_style.lookup('TLabel', 'font')).actual()
        fi['size'] = abs(fi['size']) # Why would the size be negative???

    def configure(self):
        ttk_style = self.ttk_style
        if sys.platform == 'win32':
            GroupBG = self.GroupBG
            ttk_style = ttk.Style()
            ttk_style.configure('TLabelframe', background=GroupBG)
            ttk_style.configure('TLabelframe.Label', background=GroupBG)
            ttk_style.configure('TLabel', background=GroupBG)

def StashStyle(root):
    if root is None:
        if tk._default_root is None:
            root = tk.Tk(className='stash')
            root.iconify()
        else:
            root = tk._default_root
    try:
        return root.style
    except AttributeError:
        root.style = style = _StashStyle()
        style.configure()
        return style 
