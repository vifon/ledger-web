from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import itertools
import re

from ledger_submit.models import Rule
from ledger_submit.views import check_rule
from utils import ledger_api


@login_required
def transactions(request):
    entries = reversed(list(ledger_api.Journal(request.user.ledger_path.path)))

    payee = request.GET.get('payee')
    note = request.GET.get('note')

    rule = Rule(payee=payee, note=note)

    entries = (
        entry for entry in entries
        if check_rule(entry, rule) is not None
    )

    count = request.GET.get('count')
    if count is not None:
        try:
            count = int(count)
        except ValueError:
            return JsonResponse(
                {
                    'error': {
                        'count': count,
                    }
                },
                status=422,
            )
        entries = itertools.islice(entries, count)

    return JsonResponse({'entries': list(entries)})
