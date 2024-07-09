# -*- mode: python ; coding: utf-8 -*-

import os
import pykakasi

block_cipher = None


pykakasi_dir = os.path.dirname(pykakasi.__file__)
pykakasi_data = os.path.join(pykakasi_dir, 'data')

a = Analysis(['game-translator-gui.py'],
             pathex=['path_to_your_script_directory'],
             binaries=[],
             datas=[(pykakasi_data, 'pykakasi/data')],  # 添加pykakasi数据文件
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,  
          [],
          name='game-translator-gui',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          upx_exclude=[],
          runtime_tmpdir=None,
          console=True,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )