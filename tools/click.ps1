# Click inside a window without stealing focus: post the mouse messages
# straight to its queue (SDL reads them from there). -X/-Y are client
# coordinates of the window; use -Game to pass 640x480 game coordinates
# instead and let the script scale them to the client area.
param([int]$X, [int]$Y, [string]$ProcName = "DOSBox", [int]$Count = 1,
      [switch]$Game, [int]$Right = 0)
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Clk {
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr wp, IntPtr lp);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
}
"@
$WM_MOUSEMOVE = 0x0200; $WM_LBUTTONDOWN = 0x0201; $WM_LBUTTONUP = 0x0202
$WM_RBUTTONDOWN = 0x0204; $WM_RBUTTONUP = 0x0205
$MK_LBUTTON = 1; $MK_RBUTTON = 2

$p = Get-Process -Name $ProcName -ErrorAction Stop |
     Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$h = $p.MainWindowHandle
$rc = New-Object Clk+RECT
[void][Clk]::GetClientRect($h, [ref]$rc)
$cw = $rc.Right - $rc.Left; $ch = $rc.Bottom - $rc.Top

if ($Game) { $cx = [int]($X * $cw / 640.0); $cy = [int]($Y * $ch / 480.0) }
else       { $cx = $X; $cy = $Y }

$lp = [IntPtr](($cy -shl 16) -bor ($cx -band 0xFFFF))
$down = if ($Right) { $WM_RBUTTONDOWN } else { $WM_LBUTTONDOWN }
$up   = if ($Right) { $WM_RBUTTONUP }   else { $WM_LBUTTONUP }
$mk   = if ($Right) { $MK_RBUTTON }     else { $MK_LBUTTON }

for ($i = 0; $i -lt $Count; $i++) {
  [void][Clk]::PostMessage($h, $WM_MOUSEMOVE, [IntPtr]0, $lp)
  Start-Sleep -Milliseconds 120
  [void][Clk]::PostMessage($h, $down, [IntPtr]$mk, $lp)
  Start-Sleep -Milliseconds 80
  [void][Clk]::PostMessage($h, $up, [IntPtr]0, $lp)
  Start-Sleep -Milliseconds 300
}
Write-Output "client ${cw}x${ch}: posted click at $cx,$cy"
