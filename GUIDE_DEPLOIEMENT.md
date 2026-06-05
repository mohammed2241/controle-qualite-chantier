# 🏗️ Guide de déploiement — Portail Contrôle Qualité

## Architecture choisie
```
Streamlit Cloud (gratuit)  ←→  Google Sheets (données)
                            ←→  Google Drive (photos)
GitHub (code source)
```

---

## ÉTAPE 1 — Préparer Google (compte de service)

### 1.1 — Créer un projet Google Cloud

1. Aller sur https://console.cloud.google.com
2. Cliquer **"Nouveau projet"** → nom : `controle-qualite`
3. Cliquer **"Créer"**

### 1.2 — Activer les APIs nécessaires

Dans le projet, aller dans **APIs et services > Bibliothèque**, chercher et activer :
- **Google Sheets API**
- **Google Drive API**

### 1.3 — Créer un compte de service

1. **APIs et services > Identifiants > Créer des identifiants > Compte de service**
2. Nom : `controle-qualite-bot`
3. Cliquer **Créer et continuer**, puis **OK**
4. Dans la liste des comptes de service, cliquer sur le compte créé
5. Onglet **Clés > Ajouter une clé > Créer une clé JSON**
6. Un fichier `.json` se télécharge → **gardez-le précieusement**

---

## ÉTAPE 2 — Créer le Google Sheet et le dossier Drive

### 2.1 — Google Sheet

1. Aller sur https://sheets.google.com
2. Créer un nouveau classeur, le nommer **"Remarques Qualité Chantier"**
3. Copier l'**ID** depuis l'URL :
   `https://docs.google.com/spreadsheets/d/`**`CECI_EST_L_ID`**`/edit`
4. **Partager** ce Sheet avec l'email du compte de service
   (exemple : `controle-qualite-bot@controle-qualite.iam.gserviceaccount.com`)
   → rôle **Éditeur**

### 2.2 — Dossier Google Drive pour les photos

1. Aller sur https://drive.google.com
2. Créer un dossier **"Photos Chantier QC"**
3. Clic droit > **Partager** avec l'email du compte de service → rôle **Éditeur**
4. Ouvrir le dossier, copier l'**ID** depuis l'URL :
   `https://drive.google.com/drive/folders/`**`CECI_EST_L_ID`**

---

## ÉTAPE 3 — Configurer le fichier secrets.toml

Ouvrir le fichier `.streamlit/secrets.toml` et remplir :

```toml
SHEET_ID = "l_id_copié_à_l_étape_2.1"
DRIVE_FOLDER_ID = "l_id_copié_à_l_étape_2.2"
GOOGLE_CREDENTIALS = '''
{ ... contenu_du_fichier_json_téléchargé_à_étape_1.3 ... }
'''
```

⚠️ Ce fichier est dans `.gitignore` — il ne sera jamais uploadé sur GitHub.

---

## ÉTAPE 4 — Mettre le code sur GitHub

```bash
# Dans un terminal, à la racine du dossier controle_qualite/

git init
git add app.py requirements.txt .gitignore .streamlit/config.toml
# ⚠️ NE PAS ajouter secrets.toml !

git commit -m "Initial commit — Portail Contrôle Qualité"
git branch -M main

# Créer un repository sur github.com, puis :
git remote add origin https://github.com/VOTRE_NOM/controle-qualite.git
git push -u origin main
```

---

## ÉTAPE 5 — Déployer sur Streamlit Cloud

1. Aller sur https://share.streamlit.io
2. Se connecter avec votre compte GitHub
3. Cliquer **"New app"**
4. Choisir votre repository `controle-qualite`
5. **Main file path** : `app.py`
6. Cliquer **"Advanced settings"** → onglet **Secrets**
7. Coller le **contenu complet** de votre `secrets.toml` :
   ```toml
   SHEET_ID = "..."
   DRIVE_FOLDER_ID = "..."
   GOOGLE_CREDENTIALS = '''{ ... }'''
   ```
8. Cliquer **Deploy** ✅

Votre application sera disponible sur :
`https://VOTRE_NOM-controle-qualite-app-XXXXX.streamlit.app`

---

## ÉTAPE 6 — Utiliser depuis mobile

- Ouvrir l'URL Streamlit dans un navigateur mobile (Chrome ou Safari)
- La caméra est accessible via le bouton "Ajouter des photos"
- Sur iPhone/Android, il proposera d'ouvrir la caméra directement

---

## Structure Google Sheet générée automatiquement

| ID | Date | Heure | Tranche | Immeuble | Local | Zone | Métier | Priorité | Désignation | Commentaire | Photos_URLs | Saisi_par |
|----|------|-------|---------|----------|-------|------|--------|----------|-------------|-------------|-------------|-----------|

Les liens photos pointent vers Google Drive (visibles par tous si partagés en lecture).

---

## Résumé des coûts

| Service | Coût |
|---------|------|
| Streamlit Cloud | **Gratuit** (1 app) |
| Google Sheets | **Gratuit** (jusqu'à 5 million cellules) |
| Google Drive | **Gratuit** (15 Go inclus) |
| GitHub | **Gratuit** (repository public ou privé) |

**Total : 0 €/mois** pour un chantier standard.

---

## Besoin d'aide ?

Contacter pour toute question sur le déploiement.
