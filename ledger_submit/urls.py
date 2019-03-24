from django.urls import path

from . import views

app_name = 'ledger_submit'
urlpatterns = [
    path('', views.submit_as_json, name='as_json'),
    path(
        'account_from/<str:account_from>/'
        'account_to/<str:account_to>/'
        'payee/<str:payee>/'
        'amount/<str:amount>',
        views.submit_as_url,
        name='as_url'
    ),
]
