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
            # Forcibly skip processing the rules.
            {
                'payee': 'AUCHAN WARSZAWA',
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '10 PLN',
                'skip_rules': True,
            },
            {
                'payee': 'AUCHAN WARSZAWA',
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '10.00',
                'currency': 'PLN',
            },
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
        Rule.objects.create(
            user=self.user,
            payee='AUCHAN WARSZ.*',
            new_payee='Auchan',
            account='Expenses:Food',
        )
        Rule.objects.create(
            user=self.another_user,
            payee='AUCHAN WARSZ.*',
            new_payee='Carrefour LOL',
            account='Expenses:Not Food',
        )
        Rule.objects.create(
            user=self.user,
            payee='Pizza Dominium',
            new_payee='',
            account='Expenses:Restaurants',
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


    @parameterized.expand([
        (
            # Replacement rules.
            (
                {
                    'regex': 'CARREFOUR .*',
                    'replacement': 'Carrefour',
                },
                {
                    'regex': 'CARREFOUR EXPRESS .*',
                    'replacement': 'Carrefour Express',
                },
            ),
            # Posted payee.
            'CARREFOUR EXPRESS WARSZAWA',
            # Effective payee after replacement.
            'Carrefour Express',
        ),
        (
            # Replacement rules.
            (
                {
                    'regex': 'CARREFOUR EXPRESS .*',
                    'replacement': 'Carrefour Express',
                },
                {
                    'regex': 'CARREFOUR .*',
                    'replacement': 'Carrefour',
                },
            ),
            # Posted payee.
            'CARREFOUR EXPRESS WARSZAWA',
            # Effective payee after replacement.
            'Carrefour Express',
        ),
        (
            # Replacement rules.
            (
                {
                    'regex': 'CARREFOUR .*',
                    'replacement': 'Carrefour',
                },
                {
                    'regex': 'CARREFOUR EXPRESS .*',
                    'replacement': 'Carrefour Express',
                },
            ),
            # Posted payee.
            'CARREFOUR WARSZAWA',
            # Effective payee after replacement.
            'Carrefour',
        ),
        (
            # Replacement rules.
            (
                {
                    'regex': 'CARREFOUR EXPRESS .*',
                    'replacement': 'Carrefour Express',
                },
                {
                    'regex': 'CARREFOUR .*',
                    'replacement': 'Carrefour',
                },
            ),
            # Posted payee.
            'CARREFOUR WARSZAWA',
            # Effective payee after replacement.
            'Carrefour',
        ),
    ])
    def test_rule_order(self, rules, payee, effective_payee):
        """The longest (i.e. with the largest len(payee)) rule should be
        checked first, even if we create the shorter one first.  It is
        assumed the longer the regexp, the more specific it is if
        there are multiple matches.

        """
        Rule.objects.create(
            user=self.user,
            payee=rules[0]['regex'],
            new_payee=rules[0]['replacement'],
            account='Expenses:Food',
        )
        Rule.objects.create(
            user=self.user,
            payee=rules[1]['regex'],
            new_payee=rules[1]['replacement'],
            account='Expenses:Food',
        )

        response = self.client.post(
            reverse('ledger_submit:as_json'),
            content_type='application/json',
            data={
                'token': self.good_token,
                'payee': payee,
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '12 PLN',
            },
        )
        response_dict = json.loads(response.content)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_dict['payee'], effective_payee)
