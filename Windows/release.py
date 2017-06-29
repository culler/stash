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

import os, sys, shutil
from subprocess import Popen, call, PIPE

def freshen_app(python):
    """
    Pull and build the module
    """
    os.chdir("../")
    call(["hg", "pull"])
    call(["hg", "up"])
    call([python, "setup.py", "install"])
    os.chdir("documentation")
    call(["make", "html"])
    os.chdir("..")
    if os.path.exists(r"stash\doc"):
        shutil.rmtree(r"stash\doc")
    os.rename(r"documentation\build\html", r"stash\doc")
    call([python, "setup.py", "install"])
    os.chdir("Win32")

def build_app(pyinstaller, app_name):
    """
    Build the standalone app bundle.
    """
    call([pyinstaller, app_name + ".spec"])

def package_app(app_name):
    pass
         
def do_release(python, pyinstaller, app_name):
    freshen_app(python)
    build_app(pyinstaller, app_name)
    package_app(app_name)

do_release(r"C:\Python36-x64\python",
           r"C:\Python36-x64\Scripts\pyinstaller",
           "Stash")

