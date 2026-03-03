Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
ps1 = root & "\START_DEMO_1CLICK.ps1"

If Not fso.FileExists(ps1) Then
  MsgBox "ERRORE: non trovo START_DEMO_1CLICK.ps1" & vbCrLf & ps1 & vbCrLf & "Assicurati di aver estratto tutto lo ZIP.", vbCritical, "DEMO - Avvio"
  WScript.Quit 1
End If

Set shell = CreateObject("WScript.Shell")
cmd = "cmd.exe /k powershell.exe -NoProfile -ExecutionPolicy Bypass -File """ & ps1 & """"
shell.CurrentDirectory = root
shell.Run cmd, 1, False
