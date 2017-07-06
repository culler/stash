# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
if sys.version_info[0] < 3: 
    import Tkinter as tk
    import ttk
    from tkFont import Font
else:
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
