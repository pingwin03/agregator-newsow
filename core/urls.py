"""
URL configuration for core project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

# Importuję widoki dla tokenów JWT oraz widoki do obsługi dokumentacji Swagger/OpenAPI
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Wbudowane widoki logowania i wylogowania Django
    path('accounts/login/', auth_views.LoginView.as_view(template_name='news/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Główne ścieżki aplikacji news (dashboard, tworzenie wniosków itp.)
    path('', include('news.urls')),
    
    # Endpointy API do autoryzacji opartej na tokenach JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Endpointy automatycznej dokumentacji API (Swagger / OpenAPI / ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]