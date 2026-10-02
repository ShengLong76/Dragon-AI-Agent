' Dragon AI Agent — windowless launch host.
' Shortcut target must be wscript.exe (not cscript, not powershell.exe).
' Starts start-embedded.ps1 with a hidden console; errors are MessageBox / WinForms.
' Also rewrites Desktop / Start Menu product shortcuts so an old powershell.exe
' .lnk cannot flash a console on the next open.

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

RepairProductShortcuts

' 0 = hide the host window from process create (avoids the powershell.exe flash).
' -SilentHost skips the 9119 dashboard. start-embedded.ps1 starts Docker in the tray if needed.
cmd = """" & psExe & """ -STA -NoProfile -NoLogo -NonInteractive -WindowStyle Hidden" & _
      " -ExecutionPolicy Bypass -File """ & ps1 & """ -InstallRoot """ & installRoot & """ -SilentHost"
sh.Run cmd, 0, False

Sub RepairProductShortcuts()
    Dim wsh2, fso2, desktop, smDir, wscriptExe, args, ico, targets(1), i, sc
    Set wsh2 = CreateObject("WScript.Shell")
    Set fso2 = CreateObject("Scripting.FileSystemObject")
    desktop = wsh2.SpecialFolders("Desktop")
    smDir = wsh2.ExpandEnvironmentStrings("%APPDATA%\Microsoft\Windows\Start Menu\Programs\Dragon AI Agent")
    On Error Resume Next
    If Not fso2.FolderExists(smDir) Then fso2.CreateFolder smDir
    On Error GoTo 0
    wscriptExe = wsh2.ExpandEnvironmentStrings("%SystemRoot%\System32\wscript.exe")
    args = "//nologo """ & WScript.ScriptFullName & """"
    ico = fso2.BuildPath(fso2.BuildPath(installRoot, "branding"), "dragon-ai-agent-logo.ico")
    If Not fso2.FileExists(ico) Then ico = fso2.BuildPath(installRoot, "dragon-ai-agent-logo.ico")
    targets(0) = fso2.BuildPath(desktop, "Dragon AI Agent.lnk")
    targets(1) = fso2.BuildPath(smDir, "Dragon AI Agent.lnk")
    ' Start Menu / Desktop keep only Dragon AI Agent.lnk. Drop leftovers.
    Dim retired(3), r, leftover
    retired(0) = "Dragon AI Agent Setup.lnk"
    retired(1) = "Dragon AI Agent Bot Groups.lnk"
    retired(2) = "Dragon AI Agent Dashboard.lnk"
    retired(3) = "Dragon AI Agent Profiles.lnk"
    On Error Resume Next
    For r = 0 To 3
        leftover = fso2.BuildPath(desktop, retired(r))
        If fso2.FileExists(leftover) Then fso2.DeleteFile leftover, True
        leftover = fso2.BuildPath(smDir, retired(r))
        If fso2.FileExists(leftover) Then fso2.DeleteFile leftover, True
    Next
    On Error GoTo 0
    For i = 0 To 1
        On Error Resume Next
        Set sc = wsh2.CreateShortcut(targets(i))
        sc.TargetPath = wscriptExe
        sc.Arguments = args
        sc.WorkingDirectory = installRoot
        sc.Description = "Dragon AI Agent — start the gateway and open the app"
        sc.WindowStyle = 1
        If fso2.FileExists(ico) Then sc.IconLocation = ico & ",0"
        sc.Save
        On Error GoTo 0
    Next
End Sub
