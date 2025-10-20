# getStrava

Récupérer les données Strava en Python


## Local install on a Mac

### 1. Fork project

```bash
cd /MyPythonDir
git clone https://github.com/tcrouzet/getStrava
code getStrava
```

Sous VSC ouvrir terminal et créer venv

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt --upgrade
```

### 2. Tunnel HTTPS

Pour accéder à l'API Strava, il faut lui donner une URI de callback qui récupèrera les tokens de connexion.
On va utiliser le service de redirection ngrok.

Créer un compte sur ngrok https://dashboard.ngrok.com/signup

La séquence de configuration s'affiche:
https://dashboard.ngrok.com/get-started/setup/macos

Installer ngrok en local: brew install ngrok/ngrok/ngrok

Lui associer le ngrok Token: ngrok config add-authtoken YOUR_TOKEN

Il sera sauvegardé dans ngrok.yml:

cat "/Users/thierrycrouzet/Library/Application Support/ngrok/ngrok.yml"

ngrok fournit un ngrok_URI du type:
https://uncubic-esta-amphibologically.ngrok-free.dev
qui redigera en local les requêtes qui lui seront adressées.

Dans un terminal, lancer ngrok pour activer la redirection: ngrok http 8080

### 3. Strava config

https://www.strava.com/settings/api

Créer une app avec un nom quelconque (getCrouzetDatas)

Saisir l'URI de callback: ngrok_URI (sans https://)

Récupérer STRAVA_CLIENT_ID et STRAVA_CLIENT_SECRET

### 4. configurer .env

Rename .env_stample -> .env and change values

STRAVA_REDIRECT_URI=(ngrok_URI)/auth/strava/callback

Pour créer SESSION_SECRET: python -c "import secrets; print(secrets.token_hex(64))"

### 5. Test

Lancer l'app avec:
python -m uvicorn app.main:app --reload --port 8080

Tester depuis un navigateur
http://localhost:8080/health
http://127.0.0.1:8080/health
https://(ngrok_URI)/health

Se connecter et récupérer data:
https://(ngrok_URI)/auth/strava/login

Dans mon cas:
https://uncubic-esta-amphibologically.ngrok-free.dev/health


https://uncubic-esta-amphibologically.ngrok-free.dev/auth/strava/login

https://uncubic-esta-amphibologically.ngrok-free.dev/strava/activities?athlete_id=18278258

https://uncubic-esta-amphibologically.ngrok-free.dev/strava/export_activities?athlete_id=18278258&batch_size=200

https://uncubic-esta-amphibologically.ngrok-free.dev/strava/export_streams?athlete_id=18278258