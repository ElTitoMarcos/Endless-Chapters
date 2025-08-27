import csv
from pathlib import Path

ORDERS = [
    {
        "order_id": "1001",
        "title": "El viaje de Luna",
        "email": "luna@example.com",
        "tags": "voz",
        "notes": "Niña y su gato exploran un bosque mágico",
        "cover": "hardcover",
        "size": "6x9",
        "wants_voice": "true",
        "pages": "24",
    },
    {
        "order_id": "1002",
        "title": "El faro de Mateo",
        "email": "mateo@example.com",
        "tags": "qr",
        "notes": "Niño ayuda a encender el faro antes de la tormenta",
        "cover": "paperback",
        "size": "5x8",
        "wants_voice": "false",
        "pages": "20",
    },
    {
        "order_id": "1003",
        "title": "La magia de Sofía",
        "email": "sofia@example.com",
        "tags": "voz,qr",
        "notes": "Niña encuentra un libro encantado que cobra vida",
        "cover": "hardcover",
        "size": "8x8",
        "wants_voice": "true",
        "pages": "32",
    },
    {
        "order_id": "1004",
        "title": "Aventura de Diego",
        "email": "diego@example.com",
        "tags": "",
        "notes": "Niño construye una nave espacial de cartón",
        "cover": "spiral",
        "size": "7x10",
        "wants_voice": "false",
        "pages": "28",
    },
    {
        "order_id": "1005",
        "title": "Misterio de Valentina",
        "email": "valentina@example.com",
        "tags": "qr",
        "notes": "Valentina resuelve enigmas en un museo",
        "cover": "paperback",
        "size": "5x5",
        "wants_voice": "false",
        "pages": "30",
    },
    {
        "order_id": "1006",
        "title": "Viaje de Carla",
        "email": "carla@example.com",
        "tags": "voz",
        "notes": "Carla viaja al fondo del mar con un delfín",
        "cover": "hardcover",
        "size": "6x6",
        "wants_voice": "true",
        "pages": "40",
    },
]

FIELDNAMES = [
    "order_id",
    "title",
    "email",
    "tags",
    "notes",
    "cover",
    "size",
    "wants_voice",
    "pages",
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
