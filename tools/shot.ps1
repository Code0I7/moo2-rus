# Capture one window by its owning process, the way OBS "Window Capture" does:
# PrintWindow(PW_RENDERFULLCONTENT) against the window handle, so overlays,
# other windows and the focus state do not matter and nothing is stolen from
# the user's desktop. Falls back to BitBlt, then to a screen grab.
param([string]$Out = "shot.png", [string]$ProcName = "DOSBox", [switch]$Client)
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Cap {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern IntPtr GetWindowDC(IntPtr h);
  [DllImport("user32.dll")] public static extern int ReleaseDC(IntPtr h, IntPtr hdc);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("gdi32.dll")]  public static extern bool BitBlt(IntPtr d, int x, int y, int w, int h, IntPtr s, int sx, int sy, int rop);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@

$p = Get-Process -Name $ProcName -ErrorAction Stop |
     Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
if (-not $p) { throw "no window for process $ProcName" }
$h = $p.MainWindowHandle
if ([Cap]::IsIconic($h)) { [void][Cap]::ShowWindow($h, 9); Start-Sleep -Milliseconds 500 }

$r = New-Object Cap+RECT
if ($Client) { [void][Cap]::GetClientRect($h, [ref]$r) } else { [void][Cap]::GetWindowRect($h, [ref]$r) }
$w = $r.Right - $r.Left; $ht = $r.Bottom - $r.Top
if ($w -le 0 -or $ht -le 0) { throw "bad window size ${w}x${ht}" }

function Test-Blank($bmp) {
  $step = [Math]::Max(1, [int]($bmp.Width / 40))
  for ($x = 0; $x -lt $bmp.Width; $x += $step) {
    for ($y = 0; $y -lt $bmp.Height; $y += $step) {
      $c = $bmp.GetPixel($x, $y)
      if ($c.R -ne 0 -or $c.G -ne 0 -or $c.B -ne 0) { return $false }
    }
  }
  return $true
}

$bmp = New-Object System.Drawing.Bitmap $w, $ht
$g = [System.Drawing.Graphics]::FromImage($bmp)
$hdc = $g.GetHdc()
$ok = [Cap]::PrintWindow($h, $hdc, 2)          # PW_RENDERFULLCONTENT
$g.ReleaseHdc($hdc)
$method = 'PrintWindow'

if (-not $ok -or (Test-Blank $bmp)) {
  $hdc = $g.GetHdc()
  $src = [Cap]::GetWindowDC($h)
  [void][Cap]::BitBlt($hdc, 0, 0, $w, $ht, $src, 0, 0, 0x00CC0020)   # SRCCOPY
  [void][Cap]::ReleaseDC($h, $src)
  $g.ReleaseHdc($hdc)
  $method = 'BitBlt'
  if (Test-Blank $bmp) {
    $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size)
    $method = 'Screen'
  }
}
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output "saved $Out ${w}x${ht} via $method"
