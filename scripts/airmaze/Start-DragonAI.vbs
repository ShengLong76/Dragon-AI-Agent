' Dragon AI Agent — windowless launch host.
' Shortcut target must be wscript.exe (not cscript, not powershell.exe).
' Starts start-embedded.ps1 with a hidden console; errors are MessageBox / WinForms.

Option Explicit

Dim fso, sh, here, installRoot, ps1, psExe, cmd

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

here = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = fso.BuildPath(here, "start-embedded.ps1")
installRoot = fso.GetParentFolderName(fso.GetParentFolderName(here))

If Not fso.FileExists(ps1) Then
    MsgBox "Dragon AI Agent is not installed (missing start-embedded.ps1).", 16, "Dragon AI Agent"
    WScript.Quit 1
End If

psExe = sh.ExpandEnvironmentStrings("%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe")
If Not fso.FileExists(psExe) Then
    MsgBox "Windows PowerShell was not found. Cannot start Dragon AI Agent.", 16, "Dragon AI Agent"
    WScript.Quit 1
End If

' 0 = hide the host window. -SilentHost skips the 9119 dashboard and hides any leftover console.
cmd = """" & psExe & """ -STA -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass" & _
      " -File """ & ps1 & """ -InstallRoot """ & installRoot & """ -SilentHost"
sh.Run cmd, 0, False
