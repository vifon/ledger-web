from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from parameterized import parameterized
import json

from .models import Rule, Token
from ledger_ui.models import LedgerPath


class SubmitTests(TestCase):

    good_token = 'awesometesttoken'

    def setUp(self):
        self.user = User.objects.create_user(
            username='tester',
        )
        LedgerPath.objects.create(
            user=self.user,
            path='/dev/null',
        )
        Token.objects.create(
            user=self.user,
            token=self.good_token,
        )

        self.another_user = User.objects.create_user(
            username='another',
        )
        LedgerPath.objects.create(
            user=self.another_user,
            path='/dev/null',
        )
        Token.objects.create(
            user=self.another_user,
            token='anothertoken',
        )

    @parameterized.expand([
        (
            # Modify the payee and the accounts.
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
            # Modify only accounts, don't touch payee.
            {
                'payee': 'Pizza Dominium',
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '20 PLN',
            },
            {
                'payee': 'Pizza Dominium',
                'account_to': 'Expenses:Restaurants',
                'account_from': 'Liabilities:Credit Card',
                'amount': '20.00',
                'currency': 'PLN',
            }
        ),
        (
            # No rule matched, don't modify anything.
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
        for user in [self.user, self.another_user]:
            Rule.objects.create(
                user=user,
                payee='AUCHAN WARSZ.*',
                new_payee='Auchan',
                acc_from='',
                acc_to='Expenses:Food',
            )
            Rule.objects.create(
                user=user,
                payee='Pizza Dominium',
                new_payee='',
                acc_from='',
                acc_to='Expenses:Restaurants',
            )

        response = self.client.post(
            reverse(
                'ledger_submit:as_url',
                args=[input_data[key] for key in [
                    'account_from',
                    'account_to',
                    'payee',
                    'amount',
                ]]
            ),
            content_type='application/json',
            data={'token': self.good_token},
        )
        self.assertEqual(response.status_code, 201)
        self.assertJSONEqual(
            response.content,
            expected_output,
        )

        response = self.client.post(
            reverse('ledger_submit:as_json'),
            content_type='application/json',
            data=dict(**input_data, token=self.good_token),
        )
        self.assertEqual(response.status_code, 201)
        self.assertJSONEqual(
            response.content,
            expected_output,
        )

    @parameterized.expand([
        (good_token, 201),
        ('badtesttoken', 403),
        (None, 403),
    ])
    def test_authentication(self, token, expected_status):
        input_data = {
            'payee': 'CARREFOUR WARSZAWA',
            'account_to': 'Expenses:Uncategorized',
            'account_from': 'Liabilities:Credit Card',
            'amount': '10 PLN',
        }

        if token:
            input_data.update(token=token)

        response = self.client.post(
            reverse('ledger_submit:as_json'),
            content_type='application/json',
            data=input_data,
        )
        self.assertEqual(response.status_code, expected_status)
        response_dict = json.loads(response.content)

        if expected_status == 403:
            self.assertEqual(
                response_dict,
                {
                    'error': {
                        'not_authorized': token,
                    },
                }
            )
        else:
            self.assertNotIn('error', response_dict)
