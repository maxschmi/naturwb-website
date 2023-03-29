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
from django.urls import path
from django.views.generic.base import TemplateView

from .views import (
    get_ref_view, 
    home_view, 
    result_view, 
    method_view,
    impressum_view,
    result_download,
    datenschutz_view
    )

# from dashboard.views import dashboard_view

urlpatterns = [
    path('', home_view, name="home"),
    path('get_ref/', get_ref_view, name='get_reference'),
    path('get_ref/result/', result_view, name='Ergebnis der NatUrWB Referenz'),
    path('download_result/', result_download, name='download_result'),
    path('method/', method_view, name='method'),
    path('impressum/', impressum_view, name="impressum"),
    path('datenschutz/', datenschutz_view, name="datenschutz"),
    path("robots.txt", 
         TemplateView.as_view(template_name="robots.txt", 
                              content_type="text/plain"))
]
