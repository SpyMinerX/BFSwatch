# BFSwatch – Bayerische Feuerwehr Schulungen Watcher

BFSwatch überwacht die öffentliche Restplatzbörse der Bayerischen Feuerwehr
und versendet E-Mail-Benachrichtigungen, sobald passende Lehrgänge mit
freien Plätzen veröffentlicht werden.

Überwachte Seite:
https://www.bms-fw.bayern.de/Navigation/Public/lastminute.aspx


FUNKTIONEN

- Weboberfläche
  - Auswahl eines Lehrgangs über Dropdown (automatisch geladen)
  - ODER eigene Such-Regex
  - Angabe einer E-Mail-Adresse
- Automatische tägliche Prüfung (zeitlich konfigurierbar)
- Benachrichtigung nur bei freien Plätzen > 0
- Keine doppelten Benachrichtigungen für denselben Eintrag
- SQLite-Datenbank (persistent über Docker-Volume)
- Vollständig Dockerisiert


SCHNELLSTART (DOCKER)

1. Projektverzeichnis anlegen

   mkdir bfswatch
   cd bfswatch
   mkdir data


2. Benötigte Dateien anlegen

   app.py
   requirements.txt
   Dockerfile
   docker-compose.yml


3. Container bauen und starten

   docker compose up -d --build


4. Weboberfläche öffnen

   http://localhost:5000


5. Logs anzeigen

   docker logs -f bfswatch


SMTP-KONFIGURATION

Die E-Mail-Benachrichtigung erfolgt über SMTP.
Die Konfiguration wird über Umgebungsvariablen in der docker-compose.yml gesetzt:

- SMTP_HOST
- SMTP_PORT
- SMTP_USER
- SMTP_PASS
- MAIL_FROM
- SMTP_STARTTLS

Hinweis für Gmail:
Es wird ein App-Passwort benötigt (kein normales Account-Passwort).


SCHEDULER

Standardmäßig wird die Restplatzbörse täglich um 08:05 Uhr geprüft.
Die Zeit kann über folgende Umgebungsvariablen angepasst werden:

- RUN_HOUR
- RUN_MINUTE
- TZ (z. B. Europe/Berlin)


DATENPERSISTENZ

Die SQLite-Datenbank wird im Container unter folgendem Pfad gespeichert:

/data/bfswatch.sqlite3

Dieser Pfad ist per Docker-Volume mit dem lokalen Ordner ./data verbunden.


SICHERHEITSHINWEIS

Die Weboberfläche ist standardmäßig ungeschützt.
Wenn BFSwatch außerhalb des lokalen Netzwerks erreichbar ist, wird dringend empfohlen:

- Zugriff über Firewall zu beschränken ODER
- einen Reverse Proxy mit Authentifizierung (z. B. Nginx oder Caddy) zu verwenden
