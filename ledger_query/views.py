from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

import itertools
import re

from utils import ledger_api


@login_required
def transactions(request):
    entries = reversed(list(ledger_api.Journal(request.user.ledger_path.path)))

    transaction_regexp = request.GET.get('regexp')
    if transaction_regexp is not None:
        entries = (
            entry for entry in entries
            if re.fullmatch(transaction_regexp, entry['payee'])
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
