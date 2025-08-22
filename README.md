# Tranche automation (v2)

Django app

0. Okta auth Ask Pozzan to create app on Okta
1. Get excel file. Check the excel is valid: PIANIFICAZIONE sheet, specific columns
2. Convert to csv
3. Show csv table. Make it editable. The user is responsible for the final validation.
4. Before downloading the XML, convert the edited csv to xml
5. Download xml
6. Upload xml to PIM folder (manually)

## Local Development Setup

There are two ways to set up the database for local development. Using a local Docker container is the recommended approach as it does not depend on network connectivity to GCP.

### Option 1: Local PostgreSQL with Docker (Recommended)

1.  Install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2.  Create a `.env` file from the example: `copy .env.example .env`.
3.  In the `.env` file, ensure the `DATABASE_URL` for the local Docker database is uncommented and set a password.
4.  In a terminal, start the database container: `docker-compose up -d`.
5.  You can now run the Django application locally.

### Option 2: Connecting to Cloud SQL (Requires Network Access)

### Prerequisites
1.  **Connect to the company VPN**: Your network administrator must ensure you have a route from your machine to the project's VPC network.
2.  **Authenticate with gcloud**: Run `gcloud auth application-default login`.
3.  **Create a `.env` file**: Copy `.env.example` to `.env` and fill in the secrets for local development. Uncomment the `DATABASE_URL` for Cloud SQL and use the real password.

### Running the Application
1.  If connecting to Cloud SQL, start the Cloud SQL Auth Proxy in a dedicated terminal.
    ```bash
    cloud-sql-proxy.exe --port 5432 --private-ip clz-tmp-innovation-dev:europe-west3:tranche-autom-db
    ```
2.  In a second terminal, activate your virtual environment and run the Django commands.
    ```bash
    uv run python manage.py migrate
    uv run python manage.py runserver
    ```

### Troubleshooting Cloud SQL Connection
If the Cloud SQL Auth Proxy fails to connect, your machine likely cannot reach the database's private IP. Contact your cloud infrastructure or network team for assistance. You can test connectivity with PowerShell: `Test-NetConnection <DB_PRIVATE_IP> -Port 3307`.

```bash
mkdir trance-autom
uv venv --python 3.12
uv pip install django
uv pip freeze > requirements.txt

django-admin startproject tranceautom
cd tranceautom
uv run manage.py runserver

python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

uv pip install ruff django-environ uvicorn[standard]
ruff check . --fix
ruff format .

uvicorn tranceautom.asgi:application --reload

uvicorn tranceautom.asgi:application --host 0.0.0.0 --port 8080 --workers 4

python manage.py migrate
python manage.py createsuperuser

uv pip install google-cloud-secret-manager google-cloud-storage
```

<!-- google-cloud-discoveryengine
google-cloud-resource-manager
git remote set-url origin https://mirko-bonomi@bitbucket.org/calzedoniagroup/tranche-autom.git -->
