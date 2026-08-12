from django.contrib import admin
from .models import Article
from django.contrib.auth.admin import UserAdmin
from .models import Article, User, PublicationRequest

@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    # Pola, które będą widoczne na liście (dostosuj do swoich nazw w modelu)
    list_display = ('title', 'source', 'published_at', 'is_active')
    
    # Filtry boczne przydatne do szybkiego sortowania
    list_filter = ('source', 'published_at', 'is_active')
    
    # Wyszukiwarka tekstowa
    search_fields = ('title', 'description')
    
    
# Rejestruję w panelu mój własny model użytkownika
admin.site.register(User, UserAdmin)


# admin.site.register(Article)

# Rejestruję moje żądania publikacji, żebym miał do nich podgląd
admin.site.register(PublicationRequest)