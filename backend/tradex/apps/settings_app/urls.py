from django.urls import path

from .views import AdminSettingsView, PublicPriceView, PublicSettingsView

urlpatterns = [
    path('settings/admin', AdminSettingsView.as_view(), name='get-settings'),
    path('settings/public', PublicSettingsView.as_view(), name='public-settings'),
    path('settings/price', PublicPriceView.as_view(), name='public-price'),
]
