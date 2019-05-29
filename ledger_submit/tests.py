from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

from datetime import datetime
from parameterized import parameterized

from .models import Rule, Token
from ledger_ui.models import LedgerPath


class SubmitTestsV1(TestCase):

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
            reverse('ledger_submit:json_v1'),
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
            reverse('ledger_submit:json_v1'),
            content_type='application/json',
            data=input_data,
        )
        self.assertEqual(response.status_code, expected_status)
        response_dict = response.json()

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
            reverse('ledger_submit:json_v1'),
            content_type='application/json',
            data={
                'token': self.good_token,
                'payee': payee,
                'account_to': 'Expenses:Uncategorized',
                'account_from': 'Liabilities:Credit Card',
                'amount': '12 PLN',
            },
        )
        response_dict = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_dict['payee'], effective_payee)


class SubmitTestsV2(TestCase):

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
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ('Expenses:Uncategorized', '10.00', 'PLN'),
                    ('Liabilities:Credit Card',),
                ],
            },
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ['Expenses:Uncategorized', '10.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
            }
        ),
        (
            # The same but with amount and currency joined.
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ('Expenses:Uncategorized', '10.00 PLN'),
                    ('Liabilities:Credit Card',),
                ],
            },
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ['Expenses:Uncategorized', '10.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
            }
        ),
        (
            {
                'payee': 'PIZZA DOMINIUM',
                'accounts': [
                    ('Expenses:Restaurants'   ,  '22.45', 'PLN'),
                    ('Assets:Loans:John'      ,  '22.45 PLN'),
                    ('Assets:Loans:Peter'     ,  '42.90', 'PLN'),
                    ('Liabilities:Credit Card', '-87.80', 'PLN'),
                    ('Assets:Loans:Peter'     , '-45.00', 'PLN'),
                    ('Assets:Wallet'          ,  '45.00', 'PLN'),
                ],
            },
            {
                'payee': 'PIZZA DOMINIUM',
                'accounts': [
                    ['Expenses:Restaurants'   ,  '22.45', 'PLN'],
                    ['Assets:Loans:John'      ,  '22.45', 'PLN'],
                    ['Assets:Loans:Peter'     ,  '42.90', 'PLN'],
                    ['Liabilities:Credit Card', '-87.80', 'PLN'],
                    ['Assets:Loans:Peter'     , '-45.00', 'PLN'],
                    ['Assets:Wallet'          ,  '45.00', 'PLN'],
                ],
            }
        ),
    ])
    def test_submit_basics(self, input_data, expected_output):
        expected_output.setdefault('date', datetime.now().strftime("%F"))
        response = self.client.post(
            reverse('ledger_submit:json_v2'),
            content_type='application/json',
            data=dict(**input_data, token=self.good_token),
        )
        self.assertEqual(response.status_code, 201)
        response_dict = response.json()

        self.assertEqual(
            response_dict,
            expected_output,
        )

    @parameterized.expand([
        (
            # Modify the payee and the accounts.
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ('Expenses:Uncategorized', '10.00', 'PLN'),
                    ('Liabilities:Credit Card',),
                ],
            },
            {
                'payee': 'Auchan',
                'accounts': [
                    ['Expenses:Food', '10.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
            }
        ),
        (
            # The non-default accounts are not replaced.
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ('Expenses:Restaurants', '10.00', 'PLN'),
                    ('Liabilities:Credit Card',),
                ],
            },
            {
                'payee': 'Auchan',
                'accounts': [
                    ['Expenses:Restaurants', '10.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
            }
        ),
        (
            # Forcibly skip processing the rules.
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ('Expenses:Uncategorized', '10.00', 'PLN'),
                    ('Liabilities:Credit Card',),
                ],
                'skip_rules': True,
            },
            {
                'payee': 'AUCHAN WARSZAWA',
                'accounts': [
                    ['Expenses:Uncategorized', '10.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
            }
        ),
        (
            # Modify only accounts, don't touch payee.
            {
                'payee': 'Pizza Dominium',
                'accounts': [
                    ('Expenses:Uncategorized', '20.00', 'PLN'),
                    ('Liabilities:Credit Card',),
                ],
            },
            {
                'payee': 'Pizza Dominium',
                'accounts': [
                    ['Expenses:Restaurants', '20.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
            }
        ),
        (
            # No rule matched, don't modify anything.
            {
                'payee': 'CARREFOUR WARSZAWA',
                'accounts': [
                    ('Expenses:Uncategorized', '12.00', 'PLN'),
                    ('Liabilities:Credit Card',),
                ],
            },
            {
                'payee': 'CARREFOUR WARSZAWA',
                'accounts': [
                    ['Expenses:Uncategorized', '12.00', 'PLN'],
                    ['Liabilities:Credit Card', None, None],
                ],
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

        expected_output.setdefault('date', datetime.now().strftime("%F"))
        response = self.client.post(
            reverse('ledger_submit:json_v2'),
            content_type='application/json',
            data=dict(**input_data, token=self.good_token),
        )
        self.assertEqual(response.status_code, 201)
        response_dict = response.json()

        self.assertEqual(
            response_dict,
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
            'accounts': [
                ('Expenses:Uncategorized', '10.00', 'PLN'),
                ('Liabilities:Credit Card',),
            ],
        }

        if token:
            input_data.update(token=token)

        response = self.client.post(
            reverse('ledger_submit:json_v2'),
            content_type='application/json',
            data=input_data,
        )
        self.assertEqual(response.status_code, expected_status)
        response_dict = response.json()

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
            reverse('ledger_submit:json_v2'),
            content_type='application/json',
            data={
                'token': self.good_token,
                'payee': payee,
                'accounts': [
                    ('Expenses:Uncategorized', '12', 'PLN'),
                    ('Liabilities:Credit Card',)
                ],
            },
        )
        response_dict = response.json()

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response_dict['payee'], effective_payee)
