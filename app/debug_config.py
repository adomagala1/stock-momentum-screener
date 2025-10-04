# debug_config.py
import os
from pydantic import ValidationError

print("--- START TESTU KONFIGURACJI ---")

# Sprawdzamy, czy plik .env w ogóle istnieje w oczekiwanym miejscu
# Ścieżka jest budowana tak samo jak w twoim kodzie
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.env'))
print(f"Szukam pliku .env w: {env_path}")

if os.path.exists(env_path):
    print("✅ Plik .env ZNALEZIONY.")
else:
    print("❌ BŁĄD KRYTYCZNY: Plik .env NIE ISTNIEJE w tej lokalizacji!")
    exit()  # Kończymy, jeśli nie ma pliku

# Teraz próbujemy załadować ustawienia i złapać prawdziwy błąd
try:
    # Importujemy settings DOPIERO tutaj, żeby skrypt się nie wysypał wcześniej
    from app.config import settings

    print("\n✅ SUKCES! Ustawienia załadowane poprawnie.")
    print("\n--- ZAWARTOŚĆ USTAWIEN ---")
    print(settings.model_dump())  # Drukujemy, co udało się wczytać

except ValidationError as e:
    print("\n❌ BŁĄD WALIDACJI! Oto prawdziwy powód, dlaczego apka się wysypuje:")
    print("===================================================================")
    print(e)
    print("===================================================================")
    print("\nSPRAWDŹ DOKŁADNIE WARTOŚCI W PLIKU .env!")

except Exception as e:
    print(f"\n❌ WYSTĄPIŁ INNY, NIESPODZIEWANY BŁĄD: {e}")

print("\n--- KONIEC TESTU ---")