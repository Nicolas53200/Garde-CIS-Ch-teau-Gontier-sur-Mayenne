' ============================================================
'  IGNIS - Lanceur silencieux du serveur multi-CIS
' ============================================================
'  Double-cliquer sur ce fichier pour démarrer le serveur sans
'  fenêtre noire.
'
'  - Cherche Python dans plusieurs emplacements (PATH, C:\Python*,
'    AppData\Local\Programs\Python\*)
'  - Attend jusqu'à 180 secondes que serveur_multi_cis.py soit
'    accessible (utile si le dossier est sur disque réseau ou si
'    le PC démarre avant que tout soit prêt)
'  - Installe Flask si absent
'  - Lance Python détaché (continue après fermeture du VBS)
'  - Ouvre le navigateur sur le portail IGNIS
'
'  Pour démarrer automatiquement avec Windows :
'    Win+R → shell:startup → glisser un raccourci de ce fichier
' ============================================================

Dim objShell, objFSO, strDir, strPython, strScript
Dim username, port, portUrl

Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Répertoire du script VBS
strDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

username = objShell.ExpandEnvironmentStrings("%USERNAME%")

' ─── Si le serveur tourne déjà, juste ouvrir le navigateur ────────────
If ServeurDejaActif() Then
    port = LirePort(strDir & "\settings.json")
    objShell.Run "http://localhost:" & port, 1, False
    WScript.Quit
End If

' ─── Chercher Python dans les emplacements habituels ──────────────────
Dim pythonPaths(7)
pythonPaths(0) = "python"
pythonPaths(1) = "python3"
pythonPaths(2) = "C:\Python313\python.exe"
pythonPaths(3) = "C:\Python312\python.exe"
pythonPaths(4) = "C:\Python311\python.exe"
pythonPaths(5) = "C:\Users\" & username & "\AppData\Local\Programs\Python\Python313\python.exe"
pythonPaths(6) = "C:\Users\" & username & "\AppData\Local\Programs\Python\Python312\python.exe"
pythonPaths(7) = "C:\Users\" & username & "\AppData\Local\Microsoft\WindowsApps\python.exe"

strPython = ""
Dim i, testResult
For i = 0 To 7
    On Error Resume Next
    testResult = objShell.Run("cmd /c """ & pythonPaths(i) & """ --version", 0, True)
    If Err.Number = 0 And testResult = 0 Then
        strPython = pythonPaths(i)
        Exit For
    End If
    On Error GoTo 0
Next

If strPython = "" Then
    MsgBox "Python non trouvé." & vbCrLf & vbCrLf & _
           "Installe Python 3.x depuis https://www.python.org" & vbCrLf & _
           "et coche ""Add Python to PATH"" lors de l'installation.", _
           vbCritical, "IGNIS - Erreur"
    WScript.Quit
End If

' ─── Attendre jusqu'à 180 secondes que serveur_multi_cis.py soit là ──
' Utile si le dossier est sur disque réseau ou si Windows démarre avant
' que tout soit monté.
strScript = strDir & "\serveur_multi_cis.py"

Dim tentative
tentative = 0
Do While Not objFSO.FileExists(strScript)
    tentative = tentative + 1
    If tentative > 180 Then
        MsgBox "Fichier serveur_multi_cis.py introuvable après 180 secondes." & vbCrLf & vbCrLf & _
               "Dossier attendu : " & strDir, _
               vbCritical, "IGNIS - Erreur"
        WScript.Quit
    End If
    WScript.Sleep 1000
Loop

' ─── Installer Flask si nécessaire (silencieux) ───────────────────────
objShell.Run "cmd /c """ & strPython & """ -m pip install flask --quiet", 0, True

' ─── Détacher Python du VBS pour qu'il continue à tourner ─────────────
' "cmd /c start /B" détache le processus, /B = sans nouvelle fenêtre CMD
objShell.Run "cmd /c start /B """" """ & strPython & """ """ & strScript & """", 0, False

' ─── Lire le port depuis settings.json ────────────────────────────────
port = LirePort(strDir & "\settings.json")
portUrl = "http://localhost:" & port

' ─── Attendre 3 secondes puis ouvrir le navigateur sur le portail ────
WScript.Sleep 3000
objShell.Run portUrl, 1, False

WScript.Quit


' ============================================================
'  Vérifier si serveur_multi_cis.py tourne déjà
' ============================================================
Function ServeurDejaActif()
    Dim objWMI, colProcs, p
    ServeurDejaActif = False
    On Error Resume Next
    Set objWMI = GetObject("winmgmts:\\.\root\cimv2")
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    Set colProcs = objWMI.ExecQuery( _
        "SELECT CommandLine FROM Win32_Process WHERE Name='python.exe' OR Name='pythonw.exe'")
    For Each p In colProcs
        If Not IsNull(p.CommandLine) Then
            If InStr(LCase(p.CommandLine), "serveur_multi_cis.py") > 0 Then
                ServeurDejaActif = True
                Exit For
            End If
        End If
    Next
    On Error GoTo 0
End Function


' ============================================================
'  Lire le port depuis settings.json (sinon 5010 par défaut)
' ============================================================
Function LirePort(path)
    Dim content, regex, matches, ts
    LirePort = 5010

    If Not objFSO.FileExists(path) Then Exit Function

    On Error Resume Next
    Set ts = objFSO.OpenTextFile(path, 1, False)
    If Err.Number <> 0 Then
        Err.Clear
        Exit Function
    End If
    content = ts.ReadAll
    ts.Close

    Set regex = New RegExp
    regex.Pattern = """port""\s*:\s*(\d+)"
    regex.IgnoreCase = True
    Set matches = regex.Execute(content)
    If matches.Count > 0 Then
        LirePort = CInt(matches(0).SubMatches(0))
    End If
    On Error GoTo 0
End Function
