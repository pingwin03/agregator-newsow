from rest_framework import serializers
from .models import Article, PublicationRequest, Tag

class TagSerializer(serializers.ModelSerializer):
    """Mój pomocniczy serializer do wyświetlania przypisanych tagów"""
    class Meta:
        model = Tag
        fields = ['id', 'name']

class ArticleSerializer(serializers.ModelSerializer):
    # Dołączam serializację moich nowych tagów do pełnego widoku artykułu (tylko do odczytu)
    tags = TagSerializer(many=True, read_only=True)

    class Meta:
        model = Article
        # Zlecamy DRF automatyczne przetłumaczenie wszystkich pól z naszego modelu
        fields = '__all__'


class PublicationRequestSerializer(serializers.ModelSerializer):
    # Dodaję rygorystyczną walidację dla wirtualnych pól niezbędnych do utworzenia artykułu w tle
    title = serializers.CharField(write_only=True, min_length=10, error_messages={
        'min_length': 'Tytuł musi mieć co najmniej 10 znaków.'
    })
    summary = serializers.CharField(write_only=True, min_length=20, error_messages={
        'min_length': 'Podsumowanie/treść musi zawierać co najmniej 20 znaków.'
    })
    link = serializers.URLField(required=False, allow_blank=True)
    
    # Pozwalam użytkownikowi na opcjonalne przesłanie listy tagów (np. ["AM5", "Linux"]) podczas zgłaszania
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50),
        write_only=True,
        required=False
    )

    class Meta:
        model = PublicationRequest
        # Wskazuję pola, które chcę przetwarzać i wystawiać w API (dodałem 'tags')
        fields = ['id', 'status', 'rejection_reason', 'created_at', 'title', 'summary', 'link', 'tags']
        read_only_fields = ['status', 'rejection_reason', 'created_at']

    def create(self, validated_data):
        # Wyciągam zwalidowane dane o artykule
        title = validated_data.pop('title')
        summary = validated_data.pop('summary')
        link = validated_data.pop('link', None)
        
        # Wyciągam przesłane z żądania tagi systemowe
        tags_data = validated_data.pop('tags', [])
        
        # Pobieram obiekt request z kontekstu DRF, aby ustalić, kto zgłasza propozycję
        request_obj = self.context.get('request')
        source = request_obj.user.username if request_obj and request_obj.user.is_authenticated else 'API User'
        
        # Tworzę mój nowy artykuł
        article = Article.objects.create(
            title=title,
            summary=summary,
            link=link or f"internal://api-{source}",
            source=source
        )
        
        # Obsługuję dynamiczne dodawanie tagów do mojego nowo utworzonego artykułu
        for tag_name in tags_data:
            tag_obj, created = Tag.objects.get_or_create(name=tag_name)
            article.tags.add(tag_obj)
        
        # Na koniec tworzę powiązany wniosek o publikację (domyślnie pending)
        pub_request = PublicationRequest.objects.create(
            article=article,
            status='pending'
        )
        return pub_request