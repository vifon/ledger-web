from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import os

from .utils import ledger as api


LEDGER_PATH = os.environ.get('LEDGER_PATH', '/dev/null')


@require_http_methods(['GET', 'POST'])
@csrf_exempt
def submit(request, account_from, account_to, payee, amount):
    amount = amount.replace(",", ".").strip()
    entry = api.Entry(
        payee=payee,
        account_from=account_from,
        account_to=account_to,
        amount=amount,
    )
    entry.store(LEDGER_PATH)

    response_data = {
        'entry': str(entry),
    }
    if request.method == 'GET':
        return render(
            request,
            'ledger_submit/submit.html',
            response_data,
            status=201,
        )
    elif request.method == 'POST':
        return JsonResponse(
            response_data,
            status=201,
        )


# Create your views here.
