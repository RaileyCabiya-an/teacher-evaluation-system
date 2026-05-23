# Capstone System

## Pano pag run han system

1. Clone the repository
   - Open VS CODE, pakadto ha igbaw, ig click an "Terminal" ngan ig type ini:  https://github.com/RaileyCabiya-an/teacher-evaluation-system.git

2. Go to project folder
   - type ini ha terminal:  cd Teacher-Evaluation-System

3. Create virtual environment
   - Ig type ini ha terminal:  python -m venv env

4. Activate virtual environment
   - venv\Scripts\activate 

5. Install requirements
   - ig type ini ha terminal:  pip install -r requirements.txt

6. Setup database (PostgreSQL)
- Install anay "PostgreSQL". Then open tas follow instructions. Paghimo password nga manunumduman mo. After hito, click server tas right click database. Tas create database.
- Ig name an database hin "capstone_db". After hito, ig open an iyo system ha vscode, bilnga an "settings.py" ha project folder. Pamilnga an "DATABASES" tas ig paste ini ha sakob:

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'capstone_db',
        'USER': 'postgres',
        'PASSWORD': 'your_postgres_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

7. Run migrations
- igtype ini ha terminal:  python manage.py migrate

8. Run server
- type ini ha terminal:  python manage.py runserver

Open browser
- click ini ha terminal http://127.0.0.1:8000, or copy tas paste ha browser


Adi an Email tas as Password han Admin

Email: systemadmin@gmail.com  
Password: systemadmin123
