from django.urls import path
from . import views

urlpatterns = [
    path('auth/register', views.register, name='register'),
    path('auth/register/request-otp', views.register_request_otp, name='register-request-otp'),
    path('auth/register/verify', views.register_verify, name='register-verify'),
    path('auth/register/resend-otp', views.register_resend_otp, name='register-resend-otp'),
    path('auth/forgot-password/request', views.forgot_password_request, name='forgot-password-request'),
    path('auth/forgot-password/resend', views.forgot_password_resend, name='forgot-password-resend'),
    path('auth/forgot-password/confirm', views.forgot_password_confirm, name='forgot-password-confirm'),
    path('auth/login', views.login, name='login'),
    path('auth/logout', views.logout, name='logout'),
    path('profile', views.profile, name='profile'),
]
