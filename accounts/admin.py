from django.contrib import admin

from .models import FIDOCredential

@admin.register(FIDOCredential)
class FIDOCredentialAdmin(admin.ModelAdmin):
    list_display = ('user', 'id')

