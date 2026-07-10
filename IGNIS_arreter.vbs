' ============================================================================
'  ignis_arreter.vbs
'
'  Arrete le serveur IGNIS multi-CIS lance par ignis_demarrage.vbs.
'
'  Pourquoi ce script est necessaire : ignis_demarrage.vbs lance le serveur
'  Python SANS fenetre visible (aucune console, aucune icone dans la barre
'  des taches). Il n'y a donc rien a "fermer" directement a l'ecran pour
'  l'arreter — il faut retrouver le bon processus et l'arreter explicitement.
'
'  Ce script ne tue PAS tous les processus python.exe du PC (ce qui risquerait
'  d'arreter d'autres programmes Python sans rapport). Il interroge Windows
'  (WMI) pour ne cibler QUE le processus dont la ligne de commande contient
'  exactement "serveur_multi_cis.py".
'
'  A placer dans le meme dossier que ignis_demarrage.vbs (en local, dans
'  shell:startup ou ailleurs — peu importe, contrairement au script de
'  demarrage, celui-ci n'a pas besoin d'etre lance automatiquement).
' ============================================================================

Dim objWMIService, colProcess, objProcess, trouve

Set objWMIService = GetObject("winmgmts:\\.\root\cimv2")
Set colProcess = objWMIService.ExecQuery( _
    "SELECT * FROM Win32_Process WHERE Name = 'python.exe' OR Name = 'pythonw.exe'")

trouve = False

For Each objProcess In colProcess
    If Not IsNull(objProcess.CommandLine) Then
        If InStr(1, objProcess.CommandLine, "serveur_multi_cis.py", vbTextCompare) > 0 Then
            objProcess.Terminate()
            trouve = True
        End If
    End If
Next

If trouve Then
    MsgBox "Serveur IGNIS arrete.", vbInformation, "IGNIS"
Else
    MsgBox "Aucun serveur IGNIS trouve en cours d'execution.", vbExclamation, "IGNIS"
End If
