' Startet Studforge ohne sichtbares Konsolenfenster (pythonw.exe)
Dim oShell, oFS, sDir, sLocalApp, sPython, sPythonW

Set oShell   = CreateObject("WScript.Shell")
Set oFS      = CreateObject("Scripting.FileSystemObject")
sDir         = oFS.GetParentFolderName(WScript.ScriptFullName)
sLocalApp    = oShell.ExpandEnvironmentStrings("%LOCALAPPDATA%")

Dim paths(9)
paths(0) = sLocalApp & "\Programs\Python\Python311\python.exe"
paths(1) = sLocalApp & "\Programs\Python\Python312\python.exe"
paths(2) = sLocalApp & "\Programs\Python\Python310\python.exe"
paths(3) = sLocalApp & "\Programs\Python\Python313\python.exe"
paths(4) = sLocalApp & "\Programs\Python\Python39\python.exe"
paths(5) = "C:\Python311\python.exe"
paths(6) = "C:\Python312\python.exe"
paths(7) = "C:\Python310\python.exe"
paths(8) = "C:\Python313\python.exe"
paths(9) = "C:\Python39\python.exe"

Dim i
For i = 0 To 9
    If oFS.FileExists(paths(i)) Then
        sPython = paths(i)
        Exit For
    End If
Next

If sPython = "" Then
    MsgBox "Python nicht gefunden." & vbCrLf & _
           "Bitte zuerst INSTALL.bat ausfuehren.", _
           16, "Studforge - Fehler"
    WScript.Quit 1
End If

' pythonw.exe = selbes Verzeichnis wie python.exe, kein Konsolenfenster
sPythonW = Left(sPython, Len(sPython) - 10) & "pythonw.exe"
If Not oFS.FileExists(sPythonW) Then
    sPythonW = sPython  ' Fallback auf python.exe
End If

oShell.CurrentDirectory = sDir
' WindowStyle 1 = normales Fenster; pythonw.exe oeffnet selbst kein Konsolenfenster
oShell.Run """" & sPythonW & """ """ & sDir & "\main.py""", 1, False
