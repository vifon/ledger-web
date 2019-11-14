web: env LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/app/.apt/usr/lib/ledger gunicorn ledger.wsgi
release: python manage.py migrate
