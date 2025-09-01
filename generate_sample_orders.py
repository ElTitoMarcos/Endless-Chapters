import csv
from pathlib import Path

ORDERS = [
    {
        "order_id": "1001",
        "title": "El viaje de Luna",
        "email": "luna@example.com",
        "tags": "voz",
        "notes": (
            "Luna prepara con su padre una caja de recuerdos para su hermanito "
            "recién nacido. Mientras acomodan fotos y cartas, el gato Orión los "
            "observa y ambos aprenden el valor de cuidar la historia familiar."
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
            "Mateo ayuda a su abuelo a reparar la bicicleta familiar para que su "
            "hermana pueda aprender a montar. Entre herramientas y risas, "
            "escuchan historias de juventud y fortalecen la unión de tres generaciones."
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
            "Sofía encuentra en el ático cartas que sus bisabuelos se enviaban "
            "cuando estaban lejos. Junto a su amiga Clara las lee en voz alta y "
            "descubre cómo el amor y la paciencia mantuvieron unida a la familia."
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
            "Diego y sus hermanos construyen una casa de árbol en el patio con "
            "tablas recicladas. Durante el proyecto aprenden a escucharse, compartir "
            "herramientas y crear un refugio donde la familia se reúne a contar historias."
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
            "Valentina ayuda a su madre a organizar las fotos de la familia para un "
            "álbum. Cada imagen despierta anécdotas de tíos y primos, y la niña comprende "
            "que cada recuerdo mantiene viva la memoria de quienes los quieren."
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
            "Carla graba con su hermano mayor un mensaje para la abuela que vive lejos. "
            "Mientras ensayan canciones y chistes, descubren que su voz compartida puede "
            "acortar la distancia y reforzar el cariño familiar."
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
