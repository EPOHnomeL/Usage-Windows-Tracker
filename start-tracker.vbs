' Launches the Claude Usage Tracker silently (no console window).
' Double-click this file to start the tray app.
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
pythonw = fso.BuildPath(scriptDir, ".venv\Scripts\pythonw.exe")
app = fso.BuildPath(scriptDir, "tray_app.py")

shell.CurrentDirectory = scriptDir
' 0 = hidden window, False = don't wait for it to finish
shell.Run """" & pythonw & """ """ & app & """", 0, False
