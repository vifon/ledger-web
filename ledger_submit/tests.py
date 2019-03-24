from django.test import TestCase
from django.urls import reverse

from parameterized import parameterized

from .models import Rules


class SubmitTests(TestCase):

    @parameterized.expand([
        (
            {
                'payee': 'AUCHAN WARSZAWA',
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '10 PLN',
            },
            {
                'payee': 'Auchan',
                'account_to': 'Expenses:Food',
                'account_from': 'Liabilities:Credit Card',
                'amount': '10.00',
                'currency': 'PLN',
            }
        ),
        (
            {
                'payee': 'CARREFOUR WARSZAWA',
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '12 PLN',
            },
            {
                'payee': 'CARREFOUR WARSZAWA',
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '12.00',
                'currency': 'PLN',
            }
        ),
    ])
    def test_replacements(self, input_data, expected_output):
        Rules.objects.create(
            payee='AUCHAN WARSZAWA',
            new_payee='Auchan',
            acc_from='',
            acc_to='Expenses:Food',
        )

        response = self.client.post(reverse(
            'ledger_submit:as_url',
            args=[input_data[key] for key in [
                'account_from',
                'account_to',
                'payee',
                'amount',
            ]],
        ))
        self.assertEqual(response.status_code, 201)
        self.assertJSONEqual(
            response.content,
            expected_output,
        )

        response = self.client.post(
            reverse('ledger_submit:as_json'),
            content_type='application/json',
            data=input_data,
        )
        self.assertEqual(response.status_code, 201)
        self.assertJSONEqual(
            response.content,
            expected_output,
        )
