# IGNIS - Pack multi-CIS

Ce pack met en place le principe suivant :

- 1 serveur Python unique : `serveur_multi_cis.py`
- 1 base SQLite par CIS dans le dossier `databases/`
- 1 configuration JSON par CIS dans le dossier `configs/`
- plusieurs modèles d'interface dans `interfaces/`

## CIS déjà créés

1. `chateau_gontier`
   - type : `cis_mixte`
   - base : `databases/chateau_gontier.db`
   - interface : `interfaces/Rassemblement_CIS_Mixte.html`

2. `modele_mixte_24h`
   - type : `cis_mixte_24h`
   - base : `databases/modele_mixte_24h.db`
   - interface : `interfaces/Rassemblement_CIS_Mixte_24h_BASE_A_ADAPTER.html`

3. `modele_volontaire`
   - type : `cis_volontaire`
   - base : `databases/modele_volontaire.db`
   - interface : `interfaces/Rassemblement_CIS_Volontaire.html`

## Lancer le serveur

Double-cliquer sur :

```text
lancer_multi_cis.bat
```

ou lancer :

```bash
python serveur_multi_cis.py
```

Puis ouvrir :

```text
http://localhost:8080/cis/chateau_gontier
http://localhost:8080/cis/modele_volontaire
http://localhost:8080/cis/modele_mixte_24h
```

## Ajouter un nouveau CIS par API

```bash
curl -X POST http://localhost:8080/api/cis ^
  -H "Content-Type: application/json" ^
  -d "{"super_admin_code":"CISCHATEAU53","nom":"CIS Bierné","type_cis":"cis_volontaire","admin_code":"BIERNE53"}"
```

Types disponibles :

- `cis_mixte`
- `cis_mixte_24h`
- `cis_volontaire`

## Important pour les fichiers HTML

Pour enregistrer dans la bonne base, le HTML doit appeler l'API avec le CIS choisi :

```text
/api/records?cis=modele_volontaire
```

ou envoyer dans le JSON :

```json
{ "cis": "modele_volontaire", "type": "..." }
```

Sans paramètre `cis`, le serveur utilise le CIS par défaut indiqué dans `settings.json`.
