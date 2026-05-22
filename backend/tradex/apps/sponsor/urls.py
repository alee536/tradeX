from django.urls import path

from . import views

urlpatterns = [
    path('sponsor/stats', views.SponsorStatsView.as_view(), name='sponsor-stats'),
    path('sponsor/users', views.SponsoredUsersView.as_view(), name='sponsored-users'),
    path('sponsor/access/request', views.SponsorAccessRequestView.as_view(), name='sponsor-access-request'),
    path('sponsor/ref/<slug:slug>', views.PublicSponsorRefView.as_view(), name='sponsor-public-ref'),
]
