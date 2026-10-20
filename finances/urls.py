from django.urls import path
from . import views

app_name = 'finances'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('transactions/', views.transactions_list_view, name='transactions'),
    path('transactions/batch/', views.transactions_batch_create_view, name='transactions_batch_create'),
    path('transactions/new/', views.transaction_create_view, name='transaction_create'),
    path('transactions/<int:pk>/edit/', views.transaction_update_view, name='transaction_update'),
    path('transactions/<int:pk>/delete/', views.transaction_delete_view, name='transaction_delete'),
    path('budgets/', views.budgets_list_view, name='budgets'),
    path('budgets/plan/', views.budgets_bulk_setup_view, name='budgets_bulk_setup'),
    path('budgets/new/', views.budget_create_view, name='budget_create'),
    path('budgets/<int:pk>/delete/', views.budget_delete_view, name='budget_delete'),
    path('savings/', views.savings_goals_list_view, name='savings'),
    path('savings/new/', views.savings_goal_create_view, name='savings_create'),
    path('savings/<int:pk>/contribute/', views.savings_goal_contribute_view, name='savings_contribute'),
    path('savings/<int:pk>/delete/', views.savings_goal_delete_view, name='savings_delete'),
    path('reports/', views.reports_view, name='reports'),
    path('notifications/<int:pk>/read/', views.mark_notification_read, name='notification_read'),
    path('notifications/<int:pk>/delete/', views.notification_delete_view, name='notification_delete'),
    path('notifications/read-all/', views.mark_all_notifications_read, name='notifications_read_all'),
    path('notifications/clear-all/', views.notifications_clear_all_view, name='notifications_clear_all'),
]
