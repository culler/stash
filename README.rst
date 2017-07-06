.. |copy| unicode:: 0xA9 .. copyright sign

Stash
========

Copyright |copy| 2017, Marc Culler

|

Description
-----------

Stash implements an efficient virtual filesystem which also stores
metadata for each imported file. Files are retrieved from a stash by
searching the metadata. A GUI is included for managing stashes and
accessing their files.

|

Installation
------------

Standalone applications for macOS and Windows are available in the
Downloads section.  Otherwise Stash should be installed as a standard
python package.  That is, download the archive and run:

::

  python setup.py install

Or, if you are using linux:

::

  sudo python setup.py install

To create a clickable app on linux, copy the file Linux/stash.desktop into
~/.local/share/applications and copy Linux/stash_icons.svg into
~/.local/share/icons/hicolor/scalable/apps .

|

Documentation
-------------

Online documentation is available on `Read-the-docs
<http://stash-marc-culler.readthedocs.io/en/latest/>`_.