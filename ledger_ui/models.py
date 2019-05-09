from django.contrib.auth.models import User
from django.db import models


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
        return current_end == self.new_position
