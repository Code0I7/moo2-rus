param([string]$Keys = "{ESC}", [string]$ProcName = "DOSBox", [int]$DelayMs = 600)
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class F {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool attach);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
}
"@
$p = Get-Process -Name $ProcName -ErrorAction Stop | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$h = $p.MainWindowHandle
$fg = [F]::GetForegroundWindow()
[void][F]::AttachThreadInput([F]::GetWindowThreadProcessId($fg, [IntPtr]::Zero), [F]::GetCurrentThreadId(), $true)
[void][F]::ShowWindow($h, 9)
[void][F]::SetForegroundWindow($h)
[void][F]::AttachThreadInput([F]::GetWindowThreadProcessId($fg, [IntPtr]::Zero), [F]::GetCurrentThreadId(), $false)
Start-Sleep -Milliseconds 400
foreach ($k in $Keys -split '\|') {
  [System.Windows.Forms.SendKeys]::SendWait($k)
  Start-Sleep -Milliseconds $DelayMs
}
Write-Output "sent: $Keys"
