# Generated by Django 3.2.20 on 2023-08-19 15:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_fidocredential_credential_name'),
    ]

    operations = [
        migrations.DeleteModel(
            name='FIDOCredential',
        ),
    ]
