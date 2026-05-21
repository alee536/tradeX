from django.urls import path

from . import views

urlpatterns = [
    path('settings/admin', views.AdminSettingsView.as_view(), name='get-settings'),
    path('settings/public', views.PublicSettingsView.as_view(), name='public-settings'),
    path('settings/price', views.PublicPriceView.as_view(), name='public-price'),
    path('profit/claim', views.ProfitClaimView.as_view(), name='profit-claim'),
    path('profit/history', views.ProfitClaimHistoryView.as_view(), name='profit-history'),
]
