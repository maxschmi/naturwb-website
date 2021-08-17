"""geodjango URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.conf.urls import url
from google_site_verification import GOOGLE_SITE_VERIFICATION_URL

from naturwb.views import (
    get_ref_view, 
    home_view, 
    result_view, 
    method_view,
    impressum_view
    )

# from dashboard.views import dashboard_view

urlpatterns = [
    path('', home_view, name="home"),
    path('get_ref/', get_ref_view, name='Bestimme eine NatUrWB Referenz'),
    path('get_ref/result/', result_view, name='Ergebnis der NatUrWB Referenz'),
    path('method/', method_view, name='Methodik'),
    path('admin/', admin.site.urls),
    path('impressum/', impressum_view, name="Impressum"),
    path ('accounts/', include ('django.contrib.auth.urls')),
    GOOGLE_SITE_VERIFICATION_URL
    # path('dashboard/', dashboard_view, name="Dashboard"),
    # path('django_plotly_dash/', include('django_plotly_dash.urls')),
]
