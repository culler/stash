import os
import sys
import webbrowser

if sys.platform == 'darwin':
    # Work around the fact that Python's webbrowser module
    # tries to use the default application for the file
    # extension, instead of using a real web browser.
    import plistlib
    home = os.environ['HOME']
    ls_prefs = os.path.join(home, 'Library', 'Preferences',
        'com.apple.LaunchServices',
        'com.apple.launchservices.secure.plist')
    with open(ls_prefs, 'rb') as plist_file:
        items = plistlib.load(plist_file)
    for handler in items['LSHandlers']:
        if handler.get('LSHandlerURLScheme', None) == 'http':
            break
    browser_name = handler['LSHandlerRoleAll'].split('.')[-1]
    browser = webbrowser.get(browser_name)
else:
    browser = webbrowser.get()


