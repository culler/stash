Stash
=================================
.. image:: stash_icon.gif

*Stash* is designed to help you stash your stuff, and find it again later.

*Stash* is free software and it is provided `without warranty of any kind`__.

__ http://www.gnu.org/licenses/gpl-3.0-standalone.html#section15

OK, but what is it?
-----------------------------------

A stash is an ordinary folder on your computer, but the files inside
are hidden and they are not organized by using file names.  Instead,
each stash has a list of search keys that you can use for finding the
files inside it.

For example, you might have a stash of photos, where the search keys
are: when the picture was taken; where it was taken; and who is in the
picture.  Or you might have a stash of audio files where the search
keys are the album name, the performer's name and the song title.  Or
you might have a stash of electronic bank statements where the search
keys are the account name and the date.  Or a stash of letters you
have written, with keys being the date, the recipient and the topic.
Or a list of articles that you have scanned or downloaded, with the
keys being the author, the title and the periodical where the article
was published.

When you first create a stash you are asked to choose the names and
types of the search keys for the stuff in that stash.  When you import
a file into a stash you fill in that information.  You can add
additional keys to a stash later, and you can edit the values of the
keys for each file.  But each stash uses the same set of keys for
finding its files.  So the files in one stash should all be more or
less the same type of thing.

A stash is for saving stuff that you want to be able to find and
access later.  The files in a stash are read-only, and a stash will
not accept duplicate copies of the same file.  A stash is not a good
place to put stuff that you are working on and making changes to.  If
you want to change a file in a stash, you should export it first.
 
How does it work?
--------------------------------

First you start up the Stash graphical user interface.  If you
installed a standalone Windows or Macintosh application you start it
by double-clicking the icon.  If you used easy_install to install a
python egg, you type ``stash`` at a command prompt, or click a desktop
icon linked to that command.

The File menu allows you to **Open** an existing stash or create
a **New** one.

When you create a new stash you will be first asked to choose names
and types for the search keys in that stash.  Then the new, empty
stash will be opened in a Stash Viewer.

Searching
~~~~~~~~~~~~~~~
When a stash is first opened its Viewer will show an empty list of
files in the stash.  The list is empty because you have not searched
for anything yet.  If you type some words into the text box and hit
enter, or click the **Find** button you will get a list of all files
that have a search key containing any of the words.  Or you can put
nothing in the box.  Then hitting enter or clicking **Find** will show
you all files in the stash.  (This is OK when you only have a couple
hundred files in the stash, but not so useful when you have tens
of thousands.)

Viewing
~~~~~~~~~~~~~~~
If you double click on a file in the Viewer, the file will be opened
by an appropriate application.  On the Macintosh this uses the "open"
command to choose the application, and on other platforms the file is
opened by the default browser.  (The browser needs to know how to
display files of that type.)

Other actions
~~~~~~~~~~~~~~~~ 
The "Actions" menu gives five choices:

* **Import** a file into the stash
    This does not delete the original file.  It just places a copy
    in the stash.  It is up to you to delete the original, if you want.
* **Export** a file from the stash and save it somewhere
    The stash retains its copy, but if you want to do something to the
    file, such as change it or send it to someone else, you can do that
    with the exported copy.
* **Remove** a file from the stash
    You will be given the option of exporting the file at the same time
    that you remove it from the stash.  You also have the option of
    saving the metadata (i.e. search keys) in a text file.
* edit the **Metadata** for the file
    This opens an editing window where you can change the values of the
    search keys.
* **Configure** the stash itself.
    Currently this is restricted to adding new search keys.

Why do I want this?
-----------------------

The way that people use their computers is undergoing a paradigm
shift.  The idea of hierarchical disk filesystems, where files are
stored as the leaves of a tree whose nodes are directories, goes back
to the beginning of computing.  The filesystem was designed to provide
operating systems with an efficient method for storing and retrieving
files from the disk.  It was not particularly intended to be
convenient for users.  But computer system builders found that it was
not too hard to explain the idea to users.  The users could be trained
to picture how it worked by thinking of the filesystem as a metal file
cabinet drawer in an office.  The directories could be thought of as
"folders" inside the drawer.  And the files themselves are like the
documents, each sitting inside of a folder which is carefully labeled
so that a secretary, i.e. the user, could guess which folder might
contain a needed document.

This was OK until people started being able to easily collect
thousands of documents -- by downloading them from the web, ripping
CDs, uploading photos from digital cameras and so on.  Requiring the
user to store all of the information about a file in the file name is
painful.  As the number of files grows it gets harder and harder to
think of names that will make it possible to guess what is in a file a
year from now.  And organizing files in folders does not really work
well, since each file can be in only one folder at a time.  People
need to be able to organize the same collection in different ways for
different purposes.  For example, sometimes you want to search your
email by sender, sometimes by subject, sometimes by date.  A
folder-based organizational scheme cannot be used this way.

The folder/filename paradigm is on its way out, at least for large
collections of digital documents.  Recognition of this is visible
everywhere.  Gmail does not force users to organize email messages
into folders.  Instead there is one big collection which can be
searched in various ways.  Apple has built specialized applications
for managing different types of collections: iPhoto for images, iTunes
for audio files, iMovie for video files, Address Book for vcards.
Apple's Spotlight tool is one way to attempt to work around the
inevitable inconvenience of organizing files by folders and filenames.

Stash is an attempt to provide an alternative to the out-dated
folder/filename paradigm, by providing a simple, flexible tool for
managing collections of files of any type, and for easily finding
files, without relying on folders and filenames.  It leverages the
advantages of a hierarchical filesystem without forcing users to use
it as an organizational scheme.  It imposes just enough structure to
make it easy to move collections from one place to another, even
across platforms.

What is under the hood?
-------------------------

A short answer would be "not much".  The inner workings are about 1000
lines of python code, and the graphical user interface adds another
700 lines or so.  It is true, though, that there are some complex and
powerful tools hidden under those lines.  On the other hand,
everything that Stash uses is "off the shelf" and available on nearly
all platforms.

Briefly, a stash is an ordinary directory containing a subdirectory
named ``.files`` and an SQLite3 database named ``.info``.  The files
are stored in ``.files`` and the metadata is stored in ``.info``.
Each imported file is named by its md5 hex digest, with the same
extension as the original.  The directory ``.files`` is the root
of a disk-based B-tree, for which directories are nodes and
files are leaves.  Each non-root node of the B-tree has between 128
and 255 children.  So a small stash will live in a single directory
and a stash that requires three levels will be quite large.

Installing Stash
-------------------

Stash is distributed from the Bitbucket site
https://bitbucket.org/marc_culler/stash
Standalone apps for Macintosh and (soon) Windows can be downloaded
from there.

The stash python module
---------------------------

.. toctree::
   :maxdepth: 2

   module

Indexes
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


