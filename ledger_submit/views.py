from django.conf import settings
from django.db.models.functions import Length
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from datetime import datetime
import json
import re

from .models import Rule, Token
from utils import ledger_api


def require_token(view):
    def inner(request, *args, **kwargs):
        try:
            params = json.loads(request.body)
            token = params['token']
            token_obj = Token.objects.get(token=token)
            request.user = token_obj.user
        except (KeyError, json.decoder.JSONDecodeError):
            return JsonResponse(
                {
                    'error': {
                        'not_authorized': None,
                    },
                },
                status=403,
            )
        except Token.DoesNotExist:
            return JsonResponse(
                {
                    'error': {
                        'not_authorized': token,
                    },
                },
                status=403,
            )
        else:
            return view(request, *args, **kwargs)
    return inner


def add_ledger_entry(user, account_from, account_to, payee, amount):
    ledger_path = user.ledgerpath.path
    replacement_rules = (
        Rule.objects.filter(user=user).order_by(Length('payee').desc())
    )
    for rule in replacement_rules:
        try:
            match = re.fullmatch(rule.payee, payee)
        except re.error:
            pass
        else:
            if match:
                payee = rule.new_payee or payee
                account_from = rule.acc_from or account_from
                account_to = rule.acc_to or account_to
                break

    amount = amount.replace(",", ".").strip()

    date = datetime.now()
    if settings.LEDGER_API_TIMEDELTA:
        date += settings.LEDGER_API_TIMEDELTA

    entry = ledger_api.Entry(
        payee=payee,
        account_from=account_from,
        account_to=account_to,
        amount=amount,
        date=date.strftime("%F"),
    )
    entry.store(ledger_path)
    return entry


@require_POST
@csrf_exempt
@require_token
def submit_as_url(request, account_from, account_to, payee, amount):
    entry = add_ledger_entry(request.user, account_from, account_to, payee, amount)

    return JsonResponse(
        {
            'payee': entry.payee,
            'amount': entry.amount,
            'currency': entry.currency,
            'account_from': entry.account_from,
            'account_to': entry.account_to,
        },
        status=201,
    )


@require_POST
@csrf_exempt
@require_token
def submit_as_json(request):
    params = json.loads(request.body)
    ledger_data = {
        'payee': params['payee'],
        'amount': params['amount'],
        'account_from': params['account_from'],
        'account_to': params['account_to'],
    }
    entry = add_ledger_entry(user=request.user, **ledger_data)
    return JsonResponse(
        {
            'payee': entry.payee,
            'amount': entry.amount,
            'currency': entry.currency,
            'account_from': entry.account_from,
            'account_to': entry.account_to,
        },
        status=201,
    )
