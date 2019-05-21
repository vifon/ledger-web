#!/usr/bin/env python3

import os, sys
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ledger.settings')

import django
django.setup()

from django.contrib.auth.models import User
from ledger_ui.models import LedgerPath


username = os.environ['USERNAME']
password = os.environ['PASSWORD']

if User.objects.count() == 0:
    print('Creating account {}...'.format(username))
    admin = User.objects.create_superuser(
        username=username,
        password=password,
        email=None,
    )
    admin.is_active = True
    admin.is_admin = True
    admin.save()
    ledger = LedgerPath.objects.create(
        user=admin,
        path=os.environ['LEDGER_PATH'],
    )
    ledger.save()
else:
    print('Admin accounts can only be initialized if no Accounts exist.')
