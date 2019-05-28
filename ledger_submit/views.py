from django.db.models.functions import Length
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from datetime import datetime
import json
import re

from .models import Rule, Token
from ledger_ui.models import Undo
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


def add_ledger_entry(
        user,
        account_from,
        account_to,
        payee,
        amount,
        currency=None,
        date=None,
        skip_rules=False,
):
    ledger_path = user.ledger_path.path
    if not skip_rules:
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
                    account_to = rule.account or account_to
                    break

    amount = amount.replace(",", ".").strip()

    if date is None:
        date = datetime.now().strftime("%F")

    entry = ledger_api.Entry(
        payee=payee,
        accounts=[
            (
                (account_to, amount, currency)
                if currency is not None
                else (account_to, amount)
            ),
            (account_from,)
        ],
        date=date,
    )
    old, new = ledger_api.Journal(ledger_path).append(entry)
    Undo.objects.update_or_create(
        pk=user.id,
        defaults={
            'last_entry': entry,
            'old_position': old,
            'new_position': new,
        },
    )
    return entry


@require_POST
@csrf_exempt
@require_token
def submit_as_url(request, account_from, account_to, payee, amount):
    entry = add_ledger_entry(request.user, account_from, account_to, payee, amount)

    return JsonResponse(
        {
            'payee': entry.payee,
            'amount': entry.accounts[0].amount,
            'currency': entry.accounts[0].currency,
            'account_from': entry.accounts[1].name,
            'account_to': entry.accounts[0].name,
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
    entry = add_ledger_entry(
        user=request.user,
        skip_rules=params.get('skip_rules', False),
        **ledger_data,
    )
    return JsonResponse(
        {
            'payee': entry.payee,
            'amount': entry.accounts[0].amount,
            'currency': entry.accounts[0].currency,
            'account_from': entry.accounts[1].name,
            'account_to': entry.accounts[0].name,
        },
        status=201,
    )
