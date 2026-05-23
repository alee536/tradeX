from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    # Auth
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard_alt'),
    
    # Purchases
    path('purchases/', views.purchases_list, name='purchases'),
    path('purchases/<int:purchase_id>/', views.purchase_detail, name='purchase_detail'),
    path('purchases/<int:purchase_id>/approve/', views.approve_purchase, name='approve_purchase'),
    path('purchases/<int:purchase_id>/reject/', views.reject_purchase, name='reject_purchase'),
    path('purchases/<int:purchase_id>/assign/', views.assign_coins, name='assign_coins'),
    
    # Users
    path('users/', views.users_list, name='users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Sponsor
    path('sponsor-access/', views.sponsor_access_list, name='sponsor_access'),
    path('sponsor-access/<int:request_id>/approve/', views.approve_sponsor_access, name='approve_sponsor_access'),
    path('sponsor-access/<int:request_id>/reject/', views.reject_sponsor_access, name='reject_sponsor_access'),
    path('sponsor/', views.sponsor_users_list, name='sponsor_users'),
    path('sponsor/<int:user_id>/hierarchy/', views.sponsor_hierarchy_view, name='sponsor_hierarchy'),
    path('sponsor/<int:user_id>/hierarchy/children/', views.sponsor_hierarchy_children_api, name='sponsor_hierarchy_children_api'),
    path('sponsor/hierarchy/search/', views.sponsor_hierarchy_search_api, name='sponsor_hierarchy_search_api'),
    path('sponsor-tree/', views.sponsor_tree, name='sponsor_tree'),
    
    # Withdrawals
    path('withdrawals/', views.withdrawals_list, name='withdrawals'),
    path('withdrawals/<int:withdrawal_id>/approve/', views.approve_withdrawal, name='approve_withdrawal'),
    path('withdrawals/<int:withdrawal_id>/reject/', views.reject_withdrawal, name='reject_withdrawal'),

    # Staged claims (per-purchase 50/25/25)
    path('claims/', views.claims_list, name='claims'),
    path('claims/<int:claim_id>/approve/', views.approve_claim_view, name='approve_claim'),
    path('claims/<int:claim_id>/reject/', views.reject_claim_view, name='reject_claim'),

    # Coin Settings
    path('settings/coin/', views.coin_settings, name='coin_settings'),

    # Admin notification bell
    path(
        'notifications/<int:notification_id>/read/',
        views.admin_notification_mark_read,
        name='admin_notification_mark_read',
    ),
    path(
        'notifications/read-all/',
        views.admin_notification_mark_all_read,
        name='admin_notification_mark_all_read',
    ),
]
