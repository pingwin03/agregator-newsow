import time
import string
import secrets
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .scraper import scrape_cert_polska, scrape_niebezpiecznik

@shared_task
def fetch_new_articles():
    """
    Uruchamiam automatyczne pobieranie artykułów w tle za pomocą Celery.
    Wprowadzam kontrolowane opóźnienia, aby działać kulturalnie i nie przeciążać serwerów zewnętrznych.
    """
    print("Rozpoczynam automatyczne pobieranie najnowszych zagrożeń...")
    
    # Pobieram dane z pierwszego źródła (CERT Polska)
    try:
        scrape_cert_polska()
        print("Pomyślnie pobrano dane z CERT Polska.")
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania z CERT Polska: {e}")

    # Wprowadzam bufor czasowy (kultura web scrapingu), aby nie wysyłać zapytań gradowo
    time.sleep(3)

    # Pobieram dane z drugiego źródła (Niebezpiecznik.pl)
    try:
        scrape_niebezpiecznik()
        print("Pomyślnie pobrano dane z Niebezpiecznik.pl.")
    except Exception as e:
        print(f"Wystąpił błąd podczas pobierania z Niebezpiecznik.pl: {e}")

    print("Zakończono proces pobierania ze wszystkich zewnętrznych źródeł.")

@shared_task
def send_publication_notification_email(user_email, article_title, status, reason=None):
    """
    Moje asynchroniczne zadanie wysyłające powiadomienie e-mail do użytkownika
    po rozpatrzeniu jego zgłoszenia publikacji przez oficera.
    """
    subject = f"Aktualizacja statusu zgłoszenia: {article_title}"
    
    if status == 'approved':
        message = f"Dzień dobry,\n\nTwoje zgłoszenie dotyczące artykułu '{article_title}' zostało oficjalnie zaakceptowane i opublikowane w systemie.\n\nPozdrawiamy,\nZespół Agregatora SG"
    else:
        message = f"Dzień dobry,\n\nTwoje zgłoszenie dotyczące artykułu '{article_title}' zostało niestety odrzucone.\n\nPowód odrzucenia: {reason}\n\nPozdrawiamy,\nZespół Agregatora SG"

    # Zlecam wysyłkę e-maila za pomocą wbudowanych mechanizmów Django
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
    print(f"Zadanie Celery pomyślnie wysłało powiadomienie do: {user_email}")

@shared_task
def send_initial_password_email(user_email, generated_password):
    """
    Zadanie wysyłające pierwsze, wygenerowane systemowo hasło do nowego pracownika.
    """
    subject = "Witaj w systemie Agregatora SG - Twoje dane dostępowe"
    message = f"""Dzień dobry,

Zostało dla Ciebie utworzone konto w systemie Agregatora Zagrożeń.

Twój login to: {user_email}
Twoje tymczasowe hasło to: {generated_password}

Ze względów bezpieczeństwa, przy pierwszym logowaniu system wymusi na Tobie zmianę tego hasła na nowe, zgodne z obowiązującą polityką bezpieczeństwa (min. 12 znaków, wielka i mała litera, cyfra oraz znak specjalny).

Pozdrawiamy,
Zespół IT
"""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user_email],
        fail_silently=False,
    )
    print(f"Wysłano wygenerowane hasło do: {user_email}")