export ALLOWED_HOSTS ?= *
export STATIC_ROOT ?= /var/www/ledger-web/static

export USERNAME ?= root
export PASSWORD ?= change_me
export LEDGER_PATH ?= $(HOME)/ledger.dat

all:
	@ echo "Usage:"
	@ echo '  make prod STATIC_ROOT=/var/www/ledger-web/static/ ALLOWED_HOSTS="foo.example.com bar.example.com"'
	@ echo '  make admin_account USERNAME=root PASSWORD=something_safe LEDGER_PATH=$$HOME/ledger.dat'
	@ echo '  make use_postgres'

prod:
	./scripts/prepare_prod.pl ledger/settings.py
	mkdir -p $(STATIC_ROOT)
	python3 ./manage.py collectstatic --no-input

db:
	python3 ./manage.py migrate

use_postgres:
	./scripts/switch_to_postgres.pl ledger/settings.py

admin_account:
	touch $(LEDGER_PATH)
	python3 ./scripts/set_up_admin.py $(USERNAME) $(PASSWORD) $(LEDGER_PATH)
