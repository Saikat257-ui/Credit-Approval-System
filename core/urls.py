from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome_view, name='welcome'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('check-eligibility/', views.CheckEligibilityView.as_view(), name='check-eligibility'),
    path('create-loan/', views.CreateLoanView.as_view(), name='create-loan'),
    path('view-loans/<int:customer_id>/', views.ViewLoansView.as_view(), name='view-loans'),
] 