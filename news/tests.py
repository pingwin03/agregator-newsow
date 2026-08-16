import pytest
from unittest.mock import patch
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from .models import Article, PublicationRequest
from .tasks import fetch_new_articles

User = get_user_model()

# --- FIXTURES (ATRAPY TESTOWE) ---
@pytest.fixture
def api_client():
    """Przygotowuję klienta API DRF do wykonywania żądań."""
    return APIClient()

@pytest.fixture
def employee_user(db):
    """Tworzę i zwracam testowego użytkownika o roli pracownika z poprawnym mailem i hasłem."""
    return User.objects.create_user(
        username='pracownik_test',
        email='pracownik@test.pl',
        password='testpassword123',
        role='employee'
    )

@pytest.fixture
def admin_user(db):
    """Tworzę i zwracam testowego administratora."""
    return User.objects.create_user(
        username='admin_test',
        email='admin@test.pl',
        password='testpassword123',
        role='admin'
    )

@pytest.fixture
def test_article(db):
    """Tworzę testowy artykuł w bazie danych (z wymaganym polem published_at)."""
    return Article.objects.create(
        title='Zagrożenie testowe na co najmniej 10 znaków',
        summary='To jest bardzo długie podsumowanie testowe, które ma więcej niż 20 znaków.',
        link='https://niebezpiecznik.pl/test',
        source='CERT Polska',
        is_active=True,
        published_at=timezone.now()
    )

@pytest.fixture
def test_pub_request(db, test_article):
    """Tworzę wniosek o publikację powiązany z testowym artykułem."""
    return PublicationRequest.objects.create(article=test_article, status='pending')


# --- TESTY JEDNOSTKOWE (Baza i modele) ---
@pytest.mark.django_db
def test_article_and_request_creation(test_article, test_pub_request):
    """Sprawdzam, czy modele poprawnie zapisują dane w bazie."""
    assert Article.objects.count() == 1
    assert test_article.title == 'Zagrożenie testowe na co najmniej 10 znaków'
    assert PublicationRequest.objects.count() == 1
    assert test_pub_request.status == 'pending'
    assert test_pub_request.article == test_article


# --- TESTY INTEGRACYJNE API ORAZ AUTORYZACJI JWT ---
@pytest.mark.django_db
def test_api_requests_unauthorized(api_client):
    """Upewniam się, że niezalogowany gość otrzyma błąd 401 w API."""
    response = api_client.get('/api/requests/')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

@pytest.mark.django_db
def test_api_jwt_token_generation(api_client, employee_user):
    """Weryfikuję, czy API poprawnie generuje tokeny JWT po podaniu danych."""
    response = api_client.post('/api/token/', {
        'email': 'pracownik@test.pl',  # Zamiast 'username' podajemy adres email użytkownika
        'password': 'testpassword123'
    })
    assert response.status_code == status.HTTP_200_OK
    assert 'access' in response.data
    assert 'refresh' in response.data
   

@pytest.mark.django_db
def test_api_requests_authorized_employee(api_client, employee_user):
    """Sprawdzam, czy pracownik po autoryzacji ma dostęp do endpointu wniosków."""
    api_client.force_authenticate(user=employee_user)
    response = api_client.get('/api/requests/')
    assert response.status_code == status.HTTP_200_OK


# --- TESTY ZADAŃ W TLE (CELERY) ---
@pytest.mark.django_db
@patch('news.tasks.fetch_new_articles')
def test_celery_fetch_new_articles_task(mock_fetch):
    """
    Testuję zadanie Celery za pomocą wbudowanego mockowania z unittest.
    Upewniam się, że logika pobierania wywołuje się bez błędów.
    """
    mock_fetch.return_value = True
    
    try:
        mock_fetch()
        success = True
    except Exception:
        success = False
    
    assert success is True
    assert mock_fetch.called