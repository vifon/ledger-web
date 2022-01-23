from django.contrib.auth.models import User
from django.db import models

from fido2.ctap2 import AttestedCredentialData

class FIDOCredential(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
    )
    raw_credential = models.BinaryField()
    credential_name = models.CharField(max_length=512, blank=True)

    @property
    def credential(self):
        return AttestedCredentialData(self.raw_credential)

    @credential.setter
    def credential(self, credential):
        self.raw_credential = bytes(credential)

    class Meta:
        unique_together = (('user', 'raw_credential'))
