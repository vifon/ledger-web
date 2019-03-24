from django.db import models


class Rules(models.Model):
    payee = models.CharField(max_length=512, primary_key=True)
    new_payee = models.CharField(max_length=512, blank=True)
    acc_from = models.CharField('Account from', max_length=512, blank=True)
    acc_to = models.CharField('Account to', max_length=512, blank=True)
