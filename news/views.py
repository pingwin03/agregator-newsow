import csv
import uuid
import secrets
import string
from datetime import timedelta
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth import get_user_model, login, update_session_auth_hash
from django.contrib import messages
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

# Importuję moduł do paginacji
from django.core.paginator import Paginator

# Importuję moduły do wyszukiwania pełnotekstowego z PostgreSQL
from django.contrib.postgres.search import SearchVector, SearchQuery

# Dodaję wymóg autoryzacji dla moich nowych endpointów API
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminOrOwnerReadOnly

from .models import Article, PublicationRequest
# Importuję mój nowy serializer
from .serializers import ArticleSerializer, PublicationRequestSerializer
from .forms import ArticleFilterForm, PublicationRequestForm, EmailRegistrationForm, SecurePasswordChangeForm

# Importuję moje zadanie Celery do wysyłania powiadomień i haseł
from .tasks import send_publication_notification_email, send_initial_password_email

User = get_user_model()

def generate_secure_password(length=14):
    """Funkcja pomocnicza generująca silne, losowe hasło startowe."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password) 
            and any(c.isdigit() for c in password) and any(c in "!@#$%^&*" for c in password)):
            return password

def public_article_list(request):
    """Główny widok strony głównej z kafelkami statystycznymi, filtrami i artykułami."""
    articles = Article.objects.filter(is_active=True).order_by('-published_at')
    
    # Domyślna liczba artykułów na stronę
    per_page = 20

    form = ArticleFilterForm(request.GET)
    if form.is_valid():
        search_query = form.cleaned_data.get('search')
        source_filter = form.cleaned_data.get('source')
        
        # Pobieram wybraną liczbę artykułów, jeśli użytkownik ją zmienił
        selected_per_page = form.cleaned_data.get('per_page')
        if selected_per_page:
            try:
                per_page = int(selected_per_page)
            except ValueError:
                pass

        if search_query:
            # Implementuję wyszukiwanie pełnotekstowe (Full-Text Search) w polach title i summary
            vector = SearchVector('title', weight='A') + SearchVector('summary', weight='B')
            query = SearchQuery(search_query)
            articles = articles.annotate(search=vector).filter(search=query)
            
        if source_filter:
            articles = articles.filter(source=source_filter)

    sources = Article.objects.values_list('source', flat=True).distinct().order_by('source')

    total_articles = Article.objects.filter(is_active=True).count()
    
    today_start = timezone.now() - timedelta(days=1)
    today_articles = Article.objects.filter(is_active=True, published_at__gte=today_start).count()
    
    active_sources_count = sources.count()

    pending_requests_count = 0
    if request.user.is_authenticated and request.user.role in ['admin', 'officer']:
        pending_requests_count = PublicationRequest.objects.filter(status='pending').count()

    # Inicjalizuję paginator
    paginator = Paginator(articles, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'articles': page_obj,  # Przekazuję obiekt strony zamiast całej listy
        'form': form,
        'sources': sources,
        'total_articles': total_articles,
        'today_articles': today_articles,
        'active_sources_count': active_sources_count,
        'pending_requests_count': pending_requests_count,
    }
    return render(request, 'news/article_list.html', context)


home_view = public_article_list
article_list = public_article_list


def register_view(request):
    """Widok rejestracji podający tylko e-mail. Hasło generowane i wysyłane w tle."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = EmailRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # Ustawiam login jako e-mail (ponieważ zmieniliśmy USERNAME_FIELD w modelu)
            user.username = form.cleaned_data['email']
            user.role = 'employee'
            # Wymuszam zmianę hasła przy pierwszym logowaniu
            user.force_password_change = True 
            
            # Generuję losowe, trudne hasło
            temp_password = generate_secure_password()
            user.set_password(temp_password)
            user.save()
            
            # Odpalam zadanie Celery, które wyśle maila
            send_initial_password_email.delay(user.email, temp_password)
            
            messages.success(request, "Konto zostało utworzone. Na podany adres e-mail zostało wysłane tymczasowe hasło startowe.")
            return redirect('login')
    else:
        form = EmailRegistrationForm()
        
    return render(request, 'news/register.html', {'form': form})


@login_required
def force_password_change_view(request):
    """Widok wymuszający zmianę hasła na bezpieczne."""
    if not request.user.force_password_change:
        return redirect('dashboard') # Jeśli nie musi zmieniać, odsyłam na pulpit
        
    if request.method == 'POST':
        form = SecurePasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            # Aktualizuję sesję, żeby nie wylogowało użytkownika po zmianie hasła
            update_session_auth_hash(request, form.user)
            # Zdejmuję flagę wymuszenia zmiany
            request.user.force_password_change = False
            request.user.save()
            
            messages.success(request, "Twoje hasło zostało pomyślnie zaktualizowane!")
            return redirect('dashboard')
    else:
        form = SecurePasswordChangeForm(user=request.user)
        
    return render(request, 'news/force_password_change.html', {'form': form})


@login_required
def dashboard_view(request):
    """Główny pulpit użytkownika po zalogowaniu."""
    # BRAMKA: Sprawdzam, czy użytkownik ma wygenerowane hasło i musi je zmienić
    if request.user.force_password_change:
        return redirect('force_password_change')
        
    user = request.user
    
    if user.role in ['admin', 'officer']:
        # Zoptymalizowałem zapytanie: pobieram zgłoszenia i od razu powiązane z nimi artykuły jednym zapytaniem JOIN
        requests_list = PublicationRequest.objects.select_related('article').filter(status='pending').order_by('-created_at')
        return render(
            request,
            'news/officer_dashboard.html',
            {'requests_list': requests_list},
        )
    else:
        # Analogiczna optymalizacja dla widoku pracownika
        my_requests = PublicationRequest.objects.select_related('article').filter(article__source=user.username).order_by('-created_at')
        return render(
            request, 
            'news/employee_dashboard.html', 
            {'my_requests': my_requests}
        )


@login_required
def create_publication_request(request):
    """Widok pozwalający pracownikom nadesłać artykuł do akceptacji z pełną walidacją."""
    if request.method == 'POST':
        form = PublicationRequestForm(request.POST)
        if form.is_valid():
            article = form.save(commit=False)
            
            if not article.link:
                article.link = f"internal://request-{uuid.uuid4()}"
                
            article.source = request.user.username
            article.published_at = timezone.now()
            article.save()

            PublicationRequest.objects.create(
                article=article, 
                status='pending'
            )

            return redirect('dashboard')
    else:
        form = PublicationRequestForm()

    return render(request, 'news/create_request.html', {'form': form})


@login_required
def review_request(request, pk):
    """Widok dla administratora/oficera do zatwierdzenia lub odrzucenia wniosku."""
    if request.user.role not in ['admin', 'officer']:
        return redirect('dashboard')

    pub_request = get_object_or_404(PublicationRequest, pk=pk)

    if request.method == 'POST':
        action_type = request.POST.get('action')
        
        # Pobieram email autora (jeśli istnieje)
        author = User.objects.filter(username=pub_request.article.source).first()
        author_email = author.email if author and author.email else "brak_emaila@wlii.nwosg"

        if action_type == 'approve':
            pub_request.status = 'approved'
            pub_request.save()
            # Uruchamiam asynchroniczne wysłanie powiadomienia
            send_publication_notification_email.delay(author_email, pub_request.article.title, 'approved')
            
        elif action_type == 'reject':
            reason = request.POST.get('rejection_reason', 'Brak podanego powodu')
            pub_request.status = 'rejected'
            pub_request.rejection_reason = reason
            pub_request.save()
            # Uruchamiam asynchroniczne wysłanie powiadomienia z powodem odrzucenia
            send_publication_notification_email.delay(author_email, pub_request.article.title, 'rejected', reason)

        return redirect('dashboard')

    return render(request, 'news/review_request.html', {'pub_request': pub_request})


# --- WIDOKI API (DRF) ---
class ArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer


class PublicationRequestViewSet(viewsets.ModelViewSet):
    queryset = PublicationRequest.objects.all()
    serializer_class = PublicationRequestSerializer
    # Wymagam, aby użytkownik API przesyłał token oraz korzystam z nowej klasy uprawnień
    permission_classes = [IsAuthenticated, IsAdminOrOwnerReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        if user.role in ['admin', 'officer']:
            return PublicationRequest.objects.select_related('article').all()
        return PublicationRequest.objects.select_related('article').filter(article__source=user.username)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        if request.user.role not in ['admin', 'officer']:
            return Response({"detail": "Brak uprawnień."}, status=status.HTTP_403_FORBIDDEN)
            
        pub_request = self.get_object()
        pub_request.status = 'approved'
        pub_request.save()
        
        author = User.objects.filter(username=pub_request.article.source).first()
        author_email = author.email if author and author.email else "brak_emaila@wlii.nwosg"
        send_publication_notification_email.delay(author_email, pub_request.article.title, 'approved')
        
        return Response({"status": "Wniosek został zatwierdzony."})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if request.user.role not in ['admin', 'officer']:
            return Response({"detail": "Brak uprawnień."}, status=status.HTTP_403_FORBIDDEN)
            
        pub_request = self.get_object()
        pub_request.status = 'rejected'
        reason = request.data.get('reason', 'Brak podanego powodu')
        pub_request.rejection_reason = reason
        pub_request.save()
        
        author = User.objects.filter(username=pub_request.article.source).first()
        author_email = author.email if author and author.email else "brak_emaila@wlii.nwosg"
        send_publication_notification_email.delay(author_email, pub_request.article.title, 'rejected', reason)
        
        return Response({"status": "Wniosek został odrzucony."})


class DailyReportViewSet(viewsets.ViewSet):
    """
    Nowy widok generujący zestawienie najnowszych zagrożeń w formacie CSV,
    dostępny wyłącznie dla funkcjonariuszy i administratorów.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def export_csv(self, request):
        if request.user.role not in ['admin', 'officer']:
            return Response({"detail": "Brak uprawnień do generowania raportów."}, status=status.HTTP_403_FORBIDDEN)

        time_threshold = timezone.now() - timedelta(days=1)
        recent_requests = PublicationRequest.objects.select_related('article').prefetch_related('article__tags').filter(
            status='approved',
            updated_at__gte=time_threshold
        ).order_by('-updated_at')

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="raport_zagrozen_24h.csv"'

        writer = csv.writer(response)
        writer.writerow(['Tytul', 'Zrodlo', 'Tagi Systemowe', 'Link', 'Data Akceptacji'])

        for pub_request in recent_requests:
            article = pub_request.article
            tags_str = ", ".join([tag.name for tag in article.tags.all()])
            writer.writerow([
                article.title,
                article.get_source_display(),
                tags_str,
                article.link,
                pub_request.updated_at.strftime("%Y-%m-%d %H:%M")
            ])

        return response