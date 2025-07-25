# Trance automation

Django app

1. Get excel file
2. Convert to csv (?)
3. Convert to xml
4. User validation (FE preview)
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
