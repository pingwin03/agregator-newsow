from django.db import models
from django.contrib.auth.models import AbstractUser

class Tag(models.Model):
    """Mój nowy model do zaawansowanego tagowania (np. AM5, Cisco, Linux)"""
    name = models.CharField(max_length=50, unique=True, verbose_name="Nazwa tagu")

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tagi"
        ordering = ['name']

    def __str__(self):
        return self.name

class Article(models.Model):
    # Dostępne źródła danych w systemie
    SOURCE_CHOICES = [
        ('CERT', 'CERT Polska'),
        ('CSIRT', 'CSIRT GOV'),
        ('Niebezpiecznik', 'Niebezpiecznik'),
        ('OTHER', 'Inne'),
    ]

    title = models.CharField(max_length=255, verbose_name="Tytuł")
    link = models.URLField(unique=True, verbose_name="Link do artykułu")
    summary = models.TextField(verbose_name="Podsumowanie/Treść")
    source = models.CharField(max_length=50, choices=SOURCE_CHOICES, default='OTHER', verbose_name="Źródło")
    image_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="Miniatura")
    published_at = models.DateTimeField(verbose_name="Data publikacji")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Dodano do systemu")
    is_active = models.BooleanField(default=True, verbose_name="Aktywny")
    
    # Dodaję relację wiele-do-wielu, aby swobodnie przypisywać tagi infrastrukturalne do artykułów
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles', verbose_name="Tagi systemowe")

    class Meta:
        ordering = ['-published_at']
        verbose_name = "Artykuł"
        verbose_name_plural = "Artykuły"

    def __str__(self):
        return self.title
    
    
class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('officer', 'Funkcjonariusz'),
        ('employee', 'Pracownik cywilny'),
    ]
    
    # Przebudowuję model, aby e-mail był wymagany, unikalny i pełnił rolę loginu
    email = models.EmailField(unique=True, verbose_name="Adres E-mail")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='employee')
    
    # Nowe pole wymuszające zmianę wygenerowanego hasła
    force_password_change = models.BooleanField(default=False, verbose_name="Wymaga zmiany hasła")

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # 'username' zostaje w tle, ale logujemy się mailem

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"


class PublicationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Oczekujące'),
        ('approved', 'Zatwierdzone'),
        ('rejected', 'Odrzucone'),
    ]
    
    article = models.OneToOneField('Article', on_delete=models.CASCADE, related_name='publication_request')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Powód odrzucenia")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Zgłoszenie dla: {self.article.title} - {self.get_status_display()}"