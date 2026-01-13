.PHONY: venv install dev css-watch css-build migrate collectstatic check security-scan

venv:
	python3 -m venv .venv

install: venv
	. .venv/bin/activate && pip install -r requirements.txt

dev:
	. .venv/bin/activate && python manage.py runserver

migrate:
	. .venv/bin/activate && python manage.py migrate

collectstatic:
	. .venv/bin/activate && python manage.py collectstatic --noinput

check:
	. .venv/bin/activate && python manage.py check

css-watch:
	npm run watch:css

css-build:
	npm run build:css

security-scan:
	bash scripts/security/scan_secrets.sh
