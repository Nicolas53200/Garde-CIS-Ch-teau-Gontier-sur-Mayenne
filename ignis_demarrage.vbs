' ============================================================================
'  ignis_demarrage.vbs
'
'  IMPORTANT — OU PLACER CE FICHIER :
'  Ce fichier doit etre copie EN LOCAL dans le dossier Demarrage de Windows
'  (touche Windows + R, taper "shell:startup"), PAS sur le lecteur reseau, et
'  PAS sous forme de raccourci pointant vers le reseau. Raison : si Windows
'  tente de lancer un script qui se trouve lui-meme sur un lecteur reseau pas
'  encore monte, il echoue silencieusement et rien ne se passe — aucune
'  logique de reessai a l'interieur du script ne peut alors s'executer,
'  puisque le script lui-meme n'a jamais demarre. En le gardant en local, il
'  demarre toujours immediatement et c'est LUI qui attend patiemment que le
'  dossier reseau devienne accessible.
'
'  A CONFIGURER : renseigner ci-dessous le chemin reseau exact du dossier
'  IGNIS (lecteur mappe comme "T:\IGNIS_multi_cis" ou chemin UNC comme
'  "\\NOM-SERVEUR\transvers\temp\IGNIS_multi_cis").
' ============================================================================

Const CHEMIN_RESEAU = "T:\IGNIS_multi_cis"   ' <-- A ADAPTER

Const INTERVALLE_ATTENTE_MS = 5000    ' nouvelle tentative toutes les 5 secondes
Const TEMPS_MAX_ATTENTE_MS  = 180000  ' abandonne apres 180 secondes (3 minutes)
Const DELAI_DEMARRAGE_SERVEUR_MS = 3000  ' laisse Flask demarrer avant d'ouvrir le navigateur

Dim shell, fso, settingsPath, port, tempsEcoule, dossierTrouve

Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' ----------------------------------------------------------------------------
' 1) Attendre que le dossier reseau soit accessible (jusqu'a 180 secondes)
' ----------------------------------------------------------------------------
tempsEcoule = 0
dossierTrouve = False

Do While tempsEcoule < TEMPS_MAX_ATTENTE_MS
    If fso.FileExists(CHEMIN_RESEAU & "\serveur_multi_cis.py") Then
        dossierTrouve = True
        Exit Do
    End If
    WScript.Sleep INTERVALLE_ATTENTE_MS
    tempsEcoule = tempsEcoule + INTERVALLE_ATTENTE_MS
Loop

If Not dossierTrouve Then
    ' Le reseau n'est toujours pas accessible apres 180s : on journalise en
    ' LOCAL (puisqu'on ne peut pas ecrire sur le reseau) et on s'arrete la.
    EcrireJournalLocal "Echec : " & CHEMIN_RESEAU & " inaccessible apres 180 secondes."
    WScript.Quit
End If

' ----------------------------------------------------------------------------
' 2) Le dossier reseau est accessible : demarrer le serveur puis ouvrir le navigateur
' ----------------------------------------------------------------------------
settingsPath = CHEMIN_RESEAU & "\settings.json"
port = LireValeurJson(settingsPath, "port", "8080")

' "pushd" (et non "cd /d") pour gerer aussi bien un lecteur mappe (T:\...)
' qu'un chemin UNC (\\serveur\partage\...), que "cd /d" seul ne sait pas
' toujours utiliser comme repertoire courant.
shell.Run "cmd /c pushd """ & CHEMIN_RESEAU & """ && python serveur_multi_cis.py >> server.log 2>&1", 0, False

WScript.Sleep DELAI_DEMARRAGE_SERVEUR_MS

shell.Run "http://localhost:" & port & "/"

' ----------------------------------------------------------------------------
' Fonctions utilitaires
' ----------------------------------------------------------------------------

Function LireValeurJson(chemin, cle, valeurParDefaut)
    Dim ts, contenu, re, resultats
    LireValeurJson = valeurParDefaut
    If fso.FileExists(chemin) Then
        Set ts = fso.OpenTextFile(chemin, 1)
        contenu = ts.ReadAll
        ts.Close
        Set re = CreateObject("VBScript.RegExp")
        re.Pattern = """" & cle & """\s*:\s*""?([^"",}\s]+)""?"
        If re.Test(contenu) Then
            Set resultats = re.Execute(contenu)
            LireValeurJson = resultats(0).SubMatches(0)
        End If
    End If
End Function

Sub EcrireJournalLocal(message)
    Dim cheminLocal, ts2
    cheminLocal = shell.ExpandEnvironmentStrings("%TEMP%") & "\ignis_demarrage_erreur.log"
    Set ts2 = fso.OpenTextFile(cheminLocal, 8, True) ' 8 = ajout en fin de fichier
    ts2.WriteLine Now & " - " & message
    ts2.Close
End Sub
