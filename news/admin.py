import csv
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpResponse
from django.utils.html import format_html
from .models import Article, User, PublicationRequest

# --- AKCJE GRUPOWE (BULK ACTIONS) ---

@admin.action(description='Aktywuj zaznaczone artykuły')
def make_active(modeladmin, request, queryset):
    queryset.update(is_active=True)

@admin.action(description='Dezaktywuj zaznaczone artykuły')
def make_inactive(modeladmin, request, queryset):
    queryset.update(is_active=False)

@admin.action(description='Eksportuj zaznaczone artykuły do CSV')
def export_articles_to_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="raport_artykulow.csv"'
    
    # Dodanie BOM dla poprawnego wyświetlania polskich znaków w programie Excel
    response.write('\ufeff'.encode('utf-8'))
    
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Tytuł', 'Źródło', 'Data publikacji', 'Aktywny', 'Link'])
    
    for obj in queryset:
        writer.writerow([obj.title, obj.get_source_display(), obj.published_at, 'Tak' if obj.is_active else 'Nie', obj.link])
        
    return response


# --- INLINES ---

class PublicationRequestInline(admin.TabularInline):
    model = PublicationRequest
    extra = 0
    readonly_fields = ('status', 'created_at')


# --- REJESTRACJA MODELI W PANELU ---

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'article_link_preview', 'published_at', 'is_active')
    list_filter = ('source', 'published_at', 'is_active')
    search_fields = ('title', 'summary')
    list_editable = ('is_active',)       # Szybka zmiana statusu bezpośrednio z listy
    filter_horizontal = ('tags',)        # Wygodne zarządzanie tagami typu ManyToMany
    actions = [make_active, make_inactive, export_articles_to_csv]
    inlines = [PublicationRequestInline]

    def article_link_preview(self, obj):
        """Wyświetla klikalny link do źródła otwierający się w nowej karcie."""
        if obj.link:
            return format_html('<a href="{}" target="_blank" style="color: #0066cc; font-weight: bold;">Otwórz ↗</a>', obj.link)
        return "Brak linku"
    article_link_preview.short_description = 'Link zewnętrzny'


@admin.register(PublicationRequest)
class PublicationRequestAdmin(admin.ModelAdmin):
    list_display = ('article', 'colored_status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('article__title',)

    def colored_status(self, obj):
        """Nadaje statusom ładne, kolorowe etykiety w panelu."""
        colors = {
            'pending': '#ff9900',   # Pomarańczowy dla oczekujących
            'approved': '#28a745',  # Zielony dla zatwierdzonych
            'rejected': '#dc3545',  # Czerwony dla odrzuconych
        }
        return format_html(
            '<span style="color: white; background-color: {}; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#6c757d'),
            obj.get_status_display()
        )
    colored_status.short_description = 'Status zgłoszenia'


# Rejestracja modelu użytkownika
admin.site.register(User, UserAdmin)