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

    last_entry = models.BinaryField()
    old_position = models.PositiveIntegerField()
    new_position = models.PositiveIntegerField()

    def can_revert(self):
        with open(self.user.ledger_path.path, 'r') as ledger_file:
            current_end = ledger_file.seek(0, 2)
            if current_end != self.new_position:
                return False

            ledger_file.seek(self.old_position)
            stored_entry = str(pickle.loads(self.last_entry))
            actual_entry = ledger_file.read().rstrip()
            if stored_entry != actual_entry:
                return False

        return True
