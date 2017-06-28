# -*- mode: python -*-

block_cipher = None


a = Analysis(['Stash.py'],
             pathex=['C:\\msys64\\home\\culler\\stash\\Win32'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Stash',
          debug=False,
          strip=False,
          upx=False,
          console=True,
          icon='stash_icon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='Stash')
