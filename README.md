# Tranche automation (v2)

Django app

0. Okta auth Ask Pozzan to create app on Okta
1. Get excel file. Check the excel is valid: PIANIFICAZIONE sheet, specific columns
2. Convert to csv
3. Show csv table. Make it editable. The user is responsible for the final validation.
4. Before downloading the XML, convert the edited csv to xml
5. Download xml
6. Upload xml to PIM folder (manually)

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
git remote set-url origin https://mirko-bonomi@bitbucket.org/calzedoniagroup/trance-autom.git -->
