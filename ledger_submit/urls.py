from django.urls import path

from . import views

app_name = 'ledger_submit'
urlpatterns = [
    path('', views.submit_as_json, name='as_json'),
]
