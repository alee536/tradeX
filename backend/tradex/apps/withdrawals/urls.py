from django.urls import path

from . import views

urlpatterns = [
    path('withdrawals', views.withdrawals_list, name='withdrawals-list'),
    path('withdrawals/unlocked', views.unlocked_amount, name='unlocked-amount'),
    # ============== Per-purchase staged claim ==============
    path('claims/schedule', views.ClaimScheduleView.as_view(), name='claim-schedule'),
    path('claims', views.ClaimCreateView.as_view(), name='claim-create'),
]
