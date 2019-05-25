from django.shortcuts import render
from utils.ledger_api import Journal


class HandleExceptionsMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, Journal.LedgerCliError):
            return render(
                request,
                'ledger_ui/error.html',
                {
                    'status': 500,
                    'exception': exception.__cause__,
                },
                status=500,
            )
