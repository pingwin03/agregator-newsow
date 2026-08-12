# news/forms.py
import re
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm
from .models import Article

User = get_user_model()

class ArticleFilterForm(forms.Form):
    search = forms.CharField(
        required=False, 
        label="Szukaj w tytułach",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wpisz frazę...'})
    )
    source = forms.ChoiceField(
        required=False,
        choices=[('', 'Wszystkie źródła')] + [
            ('CERT', 'CERT Polska'),
            ('CSIRT', 'CSIRT GOV'),
            ('Niebezpiecznik', 'Niebezpiecznik'),
            ('OTHER', 'Inne'),
        ],
        label="Źródło",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    # Nowe pole do wyboru ilości artykułów na stronie
    per_page = forms.ChoiceField(
        required=False,
        choices=[('10', '10'), ('20', '20'), ('30', '30'), ('40', '40')],
        label="Wyników na stronę",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class PublicationRequestForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'summary', 'link']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Wpisz tytuł artykułu...'}),
            'summary': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Wpisz treść lub podsumowanie...'}),
            'link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
        }

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 10:
            raise forms.ValidationError("Tytuł jest za krótki. Musi mieć co najmniej 10 znaków.")
        return title

    def clean_summary(self):
        summary = self.cleaned_data.get('summary')
        if len(summary) < 20:
            raise forms.ValidationError("Podsumowanie/treść musi zawierać co najmniej 20 znaków.")
        return summary

class EmailRegistrationForm(forms.ModelForm):
    """Mój dedykowany formularz rejestracji pytający tylko o e-mail i imię."""
    first_name = forms.CharField(max_length=50, required=True, label="Imię")
    last_name = forms.CharField(max_length=50, required=True, label="Nazwisko")

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']

class SecurePasswordChangeForm(PasswordChangeForm):
    """Formularz wymuszający silne hasło (lista checklisty)."""
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        
        # Implementuję rygorystyczne zasady bezpieczeństwa hasła
        if len(password) < 12:
            raise forms.ValidationError("Hasło musi mieć minimum 12 znaków.")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Hasło musi zawierać co najmniej jedną wielką literę.")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Hasło musi zawierać co najmniej jedną małą literę.")
        if not re.search(r'[0-9]', password):
            raise forms.ValidationError("Hasło musi zawierać co najmniej jedną cyfrę.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise forms.ValidationError("Hasło musi zawierać co najmniej jeden znak specjalny.")
            
        return password