"""ledger URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from ledger_ui.views import index

urlpatterns = [
    path('', index),
    path('admin/', admin.site.urls),
    path('ledger/ui/', include('ledger_ui.urls')),
    path('ledger/submit/', include('ledger_submit.urls')),
    path('ledger/query/', include('ledger_query.urls')),
    path('accounts/', include('accounts.urls')),
]
