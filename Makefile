export ALLOWED_HOSTS ?= *
export STATIC_ROOT ?= /var/www/ledger-web/static

all:
	@ echo "Run 'env STATIC_ROOT=/var/www/ledger-web/static/ ALLOWED_HOSTS=\"foo.example.com bar.example.com\" make prod'"

prod:
	./scripts/prepare_prod.pl ledger/settings.py
	python3 ./manage.py migrate
	mkdir -p $(STATIC_ROOT)
	python3 ./manage.py collectstatic --no-input
