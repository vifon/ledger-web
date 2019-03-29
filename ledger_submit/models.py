from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models


class Rule(models.Model):
    payee = models.CharField(max_length=512, primary_key=True)
    new_payee = models.CharField(max_length=512, blank=True)
    acc_from = models.CharField(
        'Account from',
        max_length=512,
        blank=True,
    )
    acc_to = models.CharField(
        'Account to',
        max_length=512,
        blank=True,
    )


class Token(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, blank=True, null=True)
    token = models.CharField(
        max_length=256,
        validators=[MinLengthValidator(32)],
    )

    def short_token(self):
        return "{}...{}".format(
            self.token[:4],
            self.token[-4:],
        )
    short_token.short_description = 'Token (short)'
    short_token.admin_order_field = 'token'

    def __str__(self):
        return "{}({})".format(self.user, self.short_token())
