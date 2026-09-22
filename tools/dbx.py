# -*- coding: utf-8 -*-
"""Drive the DOSBox window from Python: capture it and post mouse/keys.

Same technique as shot.ps1 / click.ps1 (PrintWindow + PostMessage), so it
works without focusing the window.  Coordinates are 640x480 game pixels.

    from dbx import Dbx
    d = Dbx(); img = d.shot(); d.click(492, 226); d.key('ESC')
"""
import ctypes, ctypes.wintypes as wt, time
from PIL import Image

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP = 0x200, 0x201, 0x202
WM_RBUTTONDOWN, WM_RBUTTONUP = 0x204, 0x205
WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x100, 0x101, 0x102
VK = {'ESC': 0x1B, 'ENTER': 0x0D, 'SPACE': 0x20, 'TAB': 0x09, 'F1': 0x70}

# offset between the posted point and where the game cursor lands; posting
# the move twice (see click) makes it land exactly
OFS_X, OFS_Y = 0, 0


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', wt.DWORD), ('biWidth', wt.LONG), ('biHeight', wt.LONG),
                ('biPlanes', wt.WORD), ('biBitCount', wt.WORD), ('biCompression', wt.DWORD),
                ('biSizeImage', wt.DWORD), ('biXPelsPerMeter', wt.LONG),
                ('biYPelsPerMeter', wt.LONG), ('biClrUsed', wt.DWORD), ('biClrImportant', wt.DWORD)]


def find_window(title_part='Cpu speed'):
    found = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def cb(h, _):
        n = user32.GetWindowTextLengthW(h)
        if n and user32.IsWindowVisible(h):
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(h, buf, n + 1)
            if title_part in buf.value:
                found.append(h)
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None


class Dbx:
    def __init__(self):
        self.h = find_window()
        if not self.h:
            raise SystemExit('no DOSBox window')

    def client(self):
        r = wt.RECT()
        user32.GetClientRect(self.h, ctypes.byref(r))
        return r.right, r.bottom

    def shot(self):
        """-> PIL image of the client area scaled to 640x480"""
        w, h = self.client()
        hdc = user32.GetDC(self.h)
        mdc = gdi32.CreateCompatibleDC(hdc)
        bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
        gdi32.SelectObject(mdc, bmp)
        user32.PrintWindow(self.h, mdc, 3)       # client only + full content
        bi = BITMAPINFOHEADER()
        bi.biSize = ctypes.sizeof(bi); bi.biWidth = w; bi.biHeight = -h
        bi.biPlanes = 1; bi.biBitCount = 32
        buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(mdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
        gdi32.DeleteObject(bmp); gdi32.DeleteDC(mdc); user32.ReleaseDC(self.h, hdc)
        img = Image.frombuffer('RGB', (w, h), buf, 'raw', 'BGRX', 0, 1)
        return img.resize((640, 480), Image.NEAREST)

    def _lp(self, x, y):
        w, h = self.client()
        cx = int((x + OFS_X) * w / 640.0); cy = int((y + OFS_Y) * h / 480.0)
        return (cy << 16) | (cx & 0xFFFF)

    def move(self, x, y):
        user32.PostMessageW(self.h, WM_MOUSEMOVE, 0, self._lp(x, y))

    def click(self, x, y, right=False, pause=0.35):
        lp = self._lp(x, y)
        down, up, mk = (WM_RBUTTONDOWN, WM_RBUTTONUP, 2) if right else (WM_LBUTTONDOWN, WM_LBUTTONUP, 1)
        user32.PostMessageW(self.h, WM_MOUSEMOVE, 0, lp)
        time.sleep(0.12)
        user32.PostMessageW(self.h, WM_MOUSEMOVE, 0, lp)
        time.sleep(0.12)
        user32.PostMessageW(self.h, down, mk, lp)
        time.sleep(0.08)
        user32.PostMessageW(self.h, up, 0, lp)
        time.sleep(pause)

    def key(self, name, pause=0.3):
        vk = VK.get(name) or ord(name.upper())
        user32.PostMessageW(self.h, WM_KEYDOWN, vk, 0)
        time.sleep(0.06)
        user32.PostMessageW(self.h, WM_KEYUP, vk, 0xC0000000)
        time.sleep(pause)
