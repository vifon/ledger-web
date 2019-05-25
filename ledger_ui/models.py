from django.contrib.auth.models import User
from django.db import models

import pickle


class LedgerPath(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ledger_path",
    )
    path = models.CharField(max_length=1024)

    def __str__(self):
        return "{}: {}".format(self.user, self.path)


class Undo(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
    )

    last_entry_pickle = models.BinaryField()
    old_position = models.PositiveIntegerField()
    new_position = models.PositiveIntegerField()

    @property
    def last_entry(self):
        return pickle.loads(self.last_entry_pickle)

    @last_entry.setter
    def last_entry(self, entry):
        self.last_entry_pickle = pickle.dumps(entry)
