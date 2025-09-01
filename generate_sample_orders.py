import csv
from pathlib import Path

ORDERS = [
    {
        "order_id": "1001",
        "title": "El viaje de Luna",
        "email": "luna@example.com",
        "tags": "voz",
        "notes": "Niña y su gato exploran un bosque mágico",
        "cover": "Premium Hardcover",
        "wants_voice": "true",
        "personalized_characters": "0",
        "narration": "Narrated by your loved one",
        "revisions": "0",
    },
    {
        "order_id": "1002",
        "title": "El faro de Mateo",
        "email": "mateo@example.com",
        "tags": "qr",
        "notes": "Niño ayuda a encender el faro antes de la tormenta",
        "cover": "Standard Hardcover",
        "wants_voice": "false",
        "personalized_characters": "1",
        "narration": "None",
        "revisions": "1",
    },
    {
        "order_id": "1003",
        "title": "La magia de Sofía",
        "email": "sofia@example.com",
        "tags": "voz,qr",
        "notes": "Niña encuentra un libro encantado que cobra vida",
        "cover": "Premium Hardcover",
        "wants_voice": "true",
        "personalized_characters": "2",
        "narration": "Narrated by your loved one",
        "revisions": "2",
    },
    {
        "order_id": "1004",
        "title": "Aventura de Diego",
        "email": "diego@example.com",
        "tags": "",
        "notes": "Niño construye una nave espacial de cartón",
        "cover": "Standard Hardcover",
        "wants_voice": "false",
        "personalized_characters": "3",
        "narration": "None",
        "revisions": "3",
    },
    {
        "order_id": "1005",
        "title": "Misterio de Valentina",
        "email": "valentina@example.com",
        "tags": "qr",
        "notes": "Valentina resuelve enigmas en un museo",
        "cover": "Premium Hardcover",
        "wants_voice": "false",
        "personalized_characters": "0",
        "narration": "Narrated by your loved one",
        "revisions": "1",
    },
    {
        "order_id": "1006",
        "title": "Viaje de Carla",
        "email": "carla@example.com",
        "tags": "voz",
        "notes": "Carla viaja al fondo del mar con un delfín",
        "cover": "Standard Hardcover",
        "wants_voice": "true",
        "personalized_characters": "2",
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
