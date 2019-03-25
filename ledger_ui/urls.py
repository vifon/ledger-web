from django.urls import path

from . import views

app_name = 'ledger_ui'
urlpatterns = [
    path('', views.index, name='index'),
    path('submit/', views.submit, name='submit'),
    path('accounts/', views.accounts, name='accounts'),
]
