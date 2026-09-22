# -*- coding: utf-8 -*-
"""Where things live.

PROJ  the moo2-rus folder (tr/, cfg/, and the local backup/, text/, work/)
ROOT  the game folder it sits in (ORION150.EXE, the LBX files, 150/)

From a source checkout PROJ is the parent of tools/.  In the packaged
installer (PyInstaller, see .github/workflows/release.yml) the modules run
from a temporary folder, so PROJ is the folder of the .exe instead.
"""
import os, sys

if getattr(sys, 'frozen', False):
    PROJ = os.path.dirname(os.path.abspath(sys.executable))
else:
    PROJ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ROOT = os.path.dirname(PROJ)
