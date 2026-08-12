# Pobieram lekki obraz Pythona, aby mój kontener działał szybko
FROM python:3.12-slim
# Ustawiam zmienne środowiskowe, aby Python od razu wyświetlał logi i nie tworzył niepotrzebnych plików .pyc
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Ustawiam mój główny katalog roboczy wewnątrz kontenera na /app
WORKDIR /app

# Instaluję systemowe pakiety niezbędne do poprawnego działania sterownika PostgreSQL (psycopg2)
RUN apt-get update && apt-get install -y libpq-dev gcc

# Kopiuję plik z moimi zależnościami z lokalnego dysku do kontenera
COPY requirements.txt /app/

# Aktualizuję instalatora pakietów i instaluję wszystkie wymagane biblioteki
RUN pip install --upgrade pip && pip install -r requirements.txt

# Na koniec kopiuję cały mój kod projektu do wnętrza kontenera
COPY . /app/