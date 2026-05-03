# apps/accounts/urls.py
from django.urls import path
from .views import CookieTokenObtainView, CookieTokenRefreshView, CookieLogoutView, CurrentUserView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CookieTokenObtainView.as_view(), name='token_obtain'),
    path('token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', CookieLogoutView.as_view(), name='logout'),
    path('me/', CurrentUserView.as_view(), name='current_user'),
]