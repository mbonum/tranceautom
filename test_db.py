# import psycopg2

# try:
#     conn = psycopg2.connect(
#         host="localhost",
#         port=5432,
#         database="tranche_autom",
#         user="tranche-autom-admin",
#         password="5vnlfT4oUs9u1ZYkOT6gN%7",
#     )
#     print("✅ Direct connection successful!")
#     conn.close()
# except Exception as e:
#     print(f"❌ Direct connection failed: {e}")
import os
import django
from django.conf import settings
from django.db import connection

# Setup Django
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "tranceautom.settings"
)  # Replace with your actual settings module
django.setup()


print("Django Database Config:")
print(f"ENGINE: {settings.DATABASES['default']['ENGINE']}")
print(f"NAME: {settings.DATABASES['default']['NAME']}")
print(f"USER: {settings.DATABASES['default']['USER']}")
print(f"HOST: {settings.DATABASES['default']['HOST']}")
print(f"PORT: {settings.DATABASES['default']['PORT']}")

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        print("✅ Django connection successful!")
except Exception as e:
    print(f"❌ Django connection failed: {e}")