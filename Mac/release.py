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

import os, sys, re
from subprocess import Popen, call, PIPE
from math import ceil

def get_tk_ver(python):
    """
    Figure out which version of Tk is used by this python.
    """
    out, errors = Popen([python, "-c", "import _tkinter; print(_tkinter.TK_VERSION)"],
                    stdout = PIPE).communicate()
    return out.strip()

def freshen_app(python):
    """
    Pull and build the module
    """
    os.chdir("../")
    call(["hg", "pull"])
    call(["hg", "up"])
    call([python, "setup.py", "install"])
    os.chdir("Mac")

def build_app(python):
    """
    Build the standalone app bundle.
    """
    call([python, "setup.py", "py2app"])

def cleanup_app(python, dmg_name):
    """
    Tidy things up.
    """
    # Add a symlink so that py2app 0.13 can find the Tcl Scripts directory
    tk_ver = get_tk_ver(python)
    libdir = "dist/%s.app/Contents/lib/"%dmg_name
    scriptdir = "../Frameworks/Tk.Framework/Versions/%s"%tk_ver
    os.mkdir(libdir)
    os.symlink(scriptdir, libdir + "tk%s"%tk_ver)
    # Remove some Tk stuff we don't need
    resource_dir = 'dist/Stash.app/Contents/Frameworks/Tk.framework/Resources/'
    call(['rm', '-rf', os.path.join(resource_dir, 'Wish.app')])

def package_app(dmg_name):
    """
    Create a disk image containing the app, with a nice background and
    a symlink to the Applications folder.
    """
    image_dir = "disk_images"
    if not os.path.exists(image_dir):
        os.mkdir(image_dir)
    mount_name = os.path.join("/Volumes", dmg_name)
    dmg_path = os.path.join(image_dir, dmg_name + ".dmg")
    temp_path = os.path.join(image_dir, dmg_name + "-tmp.dmg")
    # Make sure the dmg isn't currently mounted, or this won't work.  
    while os.path.exists(mount_name):
        print("Trying to eject " + mount_name)
        os.system("hdiutil detach " + mount_name)
    # Remove old dmgs if they exist.
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    if os.path.exists(temp_path):
        os.remove(temp_path)
    # Add symlink to /Applications if not there.
    if not os.path.exists("dist/Applications"):
        os.symlink("/Applications/", "dist/Applications")

    # Copy over the background and .DS_Store file.
    call(["rm", "-rf", "dist/.background.png"])
    call(["cp", "background.png", "dist/.background.png"])
    call(["cp", "dotDS_Store", "dist/.DS_Store"])
        
    # Figure out the needed size.
    raw_size, errors = Popen(["du", "-sh", "dist"], stdout=PIPE).communicate()
    size, units = re.search("([0-9.]+)([KMG])", raw_size).groups()
    new_size = "%d" % ceil(1.2 * float(size)) + units
    # Run hdiutil to build the dmg file.:
    call(["hdiutil", "makehybrid", "-hfs", "-hfs-volume-name", dmg_name,
        "-hfs-openfolder", "dist", "dist", "-o", temp_path])
    call(["hdiutil", "convert", "-format", "UDZO", temp_path, "-o", dmg_path])
    os.remove(temp_path)
    # Delete the symlink to /Applications or egg_info will be glacial on newer setuptools.
    os.remove("dist/Applications")

def do_release(python, dmg_name):
    freshen_app(python)
    build_app(python)
    cleanup_app(python, dmg_name)
    package_app(dmg_name)

do_release('python3', 'Stash')

