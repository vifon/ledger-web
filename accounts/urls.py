from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register-fido/', views.register_fido, name='register-fido'),
    path('register-fido/begin', views.register_begin, name='register-fido_begin'),
    path('register-fido/complete', views.register_complete, name='register-fido_complete'),
    path('authenticate-fido/begin', views.authenticate_begin, name='authenticate-fido_begin'),
    path('authenticate-fido/complete', views.authenticate_complete, name='authenticate-fido_complete'),
]
