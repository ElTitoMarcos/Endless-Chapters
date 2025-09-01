import csv
from pathlib import Path

ORDERS = [
    {
        "order_id": "1001",
        "title": "El viaje de Luna",
        "email": "luna@example.com",
        "tags": "voz",
        "notes": (
            "Luna y su gato Orión se internan en un bosque donde luciérnagas "
            "iluminan árboles que susurran secretos. Siguen un sendero de "
            "piedras brillantes y hallan una cascada que concede deseos a "
            "quienes creen."
        ),
        "cover": "Premium Hardcover",
        "wants_voice": "true",
        "personalized_characters": "0",
        "character_names": "",
        "narration": "Narrated by your loved one",
        "revisions": "0",
    },
    {
        "order_id": "1002",
        "title": "El faro de Mateo",
        "email": "mateo@example.com",
        "tags": "qr",
        "notes": (
            "Mateo recibe el encargo de encender el viejo faro de su abuelo "
            "ante una tormenta. Con su perro Foco, sube escalones gastados, "
            "limpia el cristal salado y logra que la luz guíe a los barcos "
            "perdidos."
        ),
        "cover": "Standard Hardcover",
        "wants_voice": "false",
        "personalized_characters": "1",
        "character_names": "Mateo",
        "narration": "None",
        "revisions": "1",
    },
    {
        "order_id": "1003",
        "title": "La magia de Sofía",
        "email": "sofia@example.com",
        "tags": "voz,qr",
        "notes": (
            "Sofía descubre en el ático de su abuela un libro cubierto de "
            "polvo. Al abrirlo, las palabras se elevan como chispas y la "
            "llevan con su amiga Clara a mares de nubes donde cada decisión "
            "cambia la aventura."
        ),
        "cover": "Premium Hardcover",
        "wants_voice": "true",
        "personalized_characters": "2",
        "character_names": "Sofía, Clara",
        "narration": "Narrated by your loved one",
        "revisions": "2",
    },
    {
        "order_id": "1004",
        "title": "Aventura de Diego",
        "email": "diego@example.com",
        "tags": "",
        "notes": (
            "Diego arma una nave de cartón con cajas viejas. Sueña viajar a "
            "Marte, pero al despegar desde su patio llega al planeta de los "
            "gatos parlantes, donde aprende paciencia, amistad y trabajo en "
            "equipo."
        ),
        "cover": "Standard Hardcover",
        "wants_voice": "false",
        "personalized_characters": "3",
        "character_names": "Diego, Luis, Ana",
        "narration": "None",
        "revisions": "3",
    },
    {
        "order_id": "1005",
        "title": "Misterio de Valentina",
        "email": "valentina@example.com",
        "tags": "qr",
        "notes": (
            "Valentina visita un museo nocturno y descubre pistas ocultas en "
            "cuadros antiguos. Con su linterna sigue símbolos hasta una sala "
            "secreta donde un busto de mármol plantea acertijos y revela "
            "tesoros familiares."
        ),
        "cover": "Premium Hardcover",
        "wants_voice": "false",
        "personalized_characters": "0",
        "character_names": "",
        "narration": "Narrated by your loved one",
        "revisions": "1",
    },
    {
        "order_id": "1006",
        "title": "Viaje de Carla",
        "email": "carla@example.com",
        "tags": "voz",
        "notes": (
            "Carla sueña con el océano y un delfín aparece para guiarla. "
            "Juntos nadan entre corales y barcos hundidos donde hallan un "
            "cofre de conchas cantoras. Cada melodía revela historias de "
            "criaturas marinas."
        ),
        "cover": "Standard Hardcover",
        "wants_voice": "true",
        "personalized_characters": "2",
        "character_names": "Carla, Delfín",
        "narration": "None",
        "revisions": "0",
    },
]

FIELDNAMES = [
    "order_id",
    "title",
    "email",
    "tags",
    "notes",
    "cover",
    "wants_voice",
    "personalized_characters",
    "character_names",
    "narration",
    "revisions",
]


def main(path: Path = Path("sample_orders.csv")) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(ORDERS)
    print(f"Generated {len(ORDERS)} orders in {path}")


if __name__ == "__main__":
    main()
