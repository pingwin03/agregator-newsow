import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from django.utils import timezone
from .models import Article

def scrape_cert_polska():
    """Scraper dla CERT Polska (działa idealnie przez RSS)"""
    url = "https://cert.pl/rss"
    headers = {'User-Agent': 'Agregator-Newsow-App/1.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            count = 0
            for item in root.findall('.//item'):
                if count >= 5: break
                title = item.find('title').text if item.find('title') is not None else "Brak tytułu"
                link = item.find('link').text if item.find('link') is not None else ""
                if link:
                    Article.objects.get_or_create(
                        link=link,
                        defaults={
                            'title': title.strip(),
                            'summary': 'Szczegóły w linku źródłowym.',
                            'source': 'CERT',
                            'published_at': timezone.now()
                        }
                    )
                    count += 1
            print("Sukces! Pomyślnie pobrano dane z CERT Polska.")
        else:
            print(f"Błąd CERT: Status {response.status_code}")
    except Exception as e:
        print(f"Błąd CERT: {e}")

def scrape_niebezpiecznik():
    """Scraper dla serwisu Niebezpiecznik.pl - wersja ze zoptymalizowanym pobieraniem miniaturek"""
    url = "https://niebezpiecznik.pl/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            count = 0
            
            for title_tag in soup.find_all(['h2', 'h3']):
                if count >= 5: 
                    break
                
                link_tag = title_tag.find('a')
                if not link_tag:
                    continue
                    
                title = title_tag.get_text(strip=True)
                href = link_tag.get('href')
                
                if len(title) < 15 or not href:
                    continue
                
                # Szukamy bloku artykułu (często <article> lub kontenera wyżej)
                container = title_tag.find_parent(['article', 'div'])
                summary = "Szczegóły w linku źródłowym."
                img_url = ""
                
                if container:
                    p_tag = container.find('p')
                    if p_tag:
                        summary = p_tag.get_text(strip=True)
                    
                    # Szukamy obrazka w kontenerze, sprawdzając różne atrybuty (src, data-src, srcset)
                    img_tag = container.find('img')
                    if img_tag:
                        img_url = (
                            img_tag.get('src') or 
                            img_tag.get('data-src') or 
                            img_tag.get('data-lazy-src')
                        )
                        # Jeśli obrazek ma srcset, bierzemy pierwszy link
                        if not img_url and img_tag.get('srcset'):
                            img_url = img_tag.get('srcset').split(',')[0].strip().split(' ')[0]
                
                if title and href:
                    Article.objects.get_or_create(
                        link=href,
                        defaults={
                            'title': title,
                            'summary': summary,
                            'source': 'Niebezpiecznik',
                            'image_url': img_url if img_url and img_url.startswith('http') else "",
                            'published_at': timezone.now()
                        }
                    )
                    count += 1
            print(f"Sukces! Pomyślnie pobrano {count} artykułów z Niebezpiecznik.pl z miniaturkami.")
        else:
            print(f"Błąd pobierania Niebezpiecznik: Status {response.status_code}")
    except Exception as e:
        print(f"Wystąpił błąd podczas scrapowania Niebezpiecznika: {e}")