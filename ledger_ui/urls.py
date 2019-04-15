from django.urls import path

from . import views

app_name = 'ledger_ui'
urlpatterns = [
    path('', views.index, name='index'),
    path('register/', views.register, name='register'),
    path('submit/', views.submit, name='submit'),
    path('balance/', views.balance, name='balance'),
    path('charts/', views.charts, name='charts'),
    path('rules/', views.RuleIndexView.as_view(), name='rules'),
    path('rule/', views.RuleCreateView.as_view(), name='rule'),
    path('rule/<int:pk>/', views.RuleEditView.as_view(), name='rule'),
    path('rule/<int:pk>/delete/', views.RuleDeleteView.as_view(), name='rule_delete'),
]
