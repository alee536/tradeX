from django.urls import path
from . import views

urlpatterns = [
    path('settings/admin', views.get_settings, name='get-settings'),
    path('settings/public', views.public_settings, name='public-settings'),
    path('settings/price', views.public_price, name='public-price'),
]
