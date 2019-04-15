from django.urls import path

from . import views

app_name = 'ledger_query'
urlpatterns = [
    path('transactions/', views.transactions, name='transactions'),
]
