from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Rejestruję moje widoki API w routerze DRF
router = DefaultRouter()
router.register(r'articles', views.ArticleViewSet, basename='article')
router.register(r'requests', views.PublicationRequestViewSet, basename='publicationrequest')
# Rejestruję mój nowy widok do obsługi raportów dziennych
router.register(r'reports', views.DailyReportViewSet, basename='report')

urlpatterns = [
    # Moje standardowe widoki HTML
    path('', views.home_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('request/new/', views.create_publication_request, name='create_request'),
    path('request/<int:pk>/review/', views.review_request, name='review_request'),
    
    # Ścieżki rejestracji i zmiany hasła
    path('register/', views.register_view, name='register'),
    path('force-password-change/', views.force_password_change_view, name='force_password_change'),
    
    # Podłączam moje endpointy API
    path('api/', include(router.urls)),
]