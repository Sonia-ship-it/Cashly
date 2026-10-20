from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('demo-login/<str:role>/', views.demo_login_view, name='demo_login'),
    path('profile/', views.profile_view, name='profile'),
]
