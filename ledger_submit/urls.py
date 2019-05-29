from django.urls import path

from . import views

app_name = 'ledger_submit'
urlpatterns = [
    path('', views.submit_as_json_v1),
    path('v1/', views.submit_as_json_v1, name='json_v1'),
    path('v2/', views.submit_as_json, name='json_v2'),
]
