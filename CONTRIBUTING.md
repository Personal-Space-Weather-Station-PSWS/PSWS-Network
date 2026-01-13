# Contributing

## Quickstart (Backend)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional if you use local env file
python manage.py migrate
python manage.py runserver
