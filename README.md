# Trance automation

1. Get excel file
2. Convert to csv
3. Convert to xml
4. Validation (FE)
5. Download xml
6. Upload xml to PIM folder

```bash
mkdir trance-autom
# Install django globally
django-admin startproject tranceautom trance-autom
uv venv --python 3.12
uv pip install django
uv pip freeze > requirements.txt
uv run manage.py runserver
```