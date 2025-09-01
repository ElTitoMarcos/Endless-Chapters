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
            "recién nacido. Revisan álbumes polvorientos, cartas que la madre "
            "escribió de niña y juguetes heredados de sus abuelos. Mientras el "
            "gato Orión los observa desde la ventana, el padre explica que cada "
            "objeto guarda parte de la historia familiar. También incluyen una "
            "medalla del bisabuelo marinero y un pañuelo bordado por la abuela, "
            "símbolos de aventuras y cuidados que esperan transmitirse. Al "
            "cerrar la caja, añaden una nota de bienvenida y prometen abrirla "
            "juntos cuando el bebé cumpla diez años, para que nunca olvide el "
            "cariño que lo esperaba antes de llegar al mundo."
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
            "hermana pueda aprender a montar. Revisan el viejo garaje, descubren "
            "herramientas oxidadas y un cuaderno con dibujos de rutas que el "
            "abuelo hacía de joven. Mientras tensan la cadena y engrasan los "
            "pedales, deciden pintar el marco con un tono azul que recuerde el "
            "cielo de las mañanas de verano. El abuelo le relata cómo esa "
            "bicicleta llevó a la familia a excursiones y ferias. La hermana "
            "observa impaciente, soñando con dar su primer paseo. Cuando "
            "finalmente terminan, dan vueltas por la calle, sintiendo que cada "
            "giro de rueda une tres generaciones y renueva las historias por "
            "venir."
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
            "cuando estaban lejos. Junto a su amiga Clara las limpia con cuidado "
            "y las lee en voz alta, descubriendo palabras de amor y planes que se "
            "cumplieron décadas después. La abuela llega con tazas de té y cuenta "
            "que esas cartas sostuvieron la relación durante la guerra. Cada "
            "sobre guarda una flor seca o una foto en blanco y negro. Inspiradas, "
            "las niñas escriben su propia carta para esconderla en la casa y que "
            "un descendiente la encuentre algún día. Al terminar, comprenden que "
            "el amor viaja en el tiempo y mantiene unida a la familia incluso "
            "cuando las distancias parecen imposibles."
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
            "tablas recicladas. Planean cada paso, dibujan planos en servilletas "
            "y negocian quién subirá primero. Su padre presta herramientas y "
            "enseña a usar la escuadra para que todo quede recto. Mientras "
            "trabajan, recuerdan historias de la infancia de sus padres y ríen de "
            "los errores. Al terminar, adornan el refugio con luces viejas y un "
            "letrero de 'Bienvenidos'. Allí guardan cómics, una radio antigua y "
            "las promesas de reunirse cada tarde para compartir aventuras. Cuando "
            "cae la noche, invitan a los vecinos a mirar las estrellas desde el "
            "nuevo mirador, sintiendo que han construido algo más que un "
            "escondite."
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
            "Valentina ayuda a su madre a organizar las fotos de la familia para "
            "un álbum. Extienden sobre la mesa retratos de bodas, vacaciones y "
            "cumpleaños olvidados. Cada imagen despierta anécdotas de tíos y "
            "primos; algunas arrugadas provocan carcajadas. Valentina pega "
            "etiquetas de colores y escribe pequeñas notas al margen para "
            "recordar quién es quién. Encuentran una foto del bisabuelo con una "
            "guitarra y deciden dedicarle una página entera. Al terminar, guardan "
            "el álbum en la sala para que cualquiera pueda hojearlo, convencidas "
            "de que cada recuerdo mantiene viva la memoria de quienes las quieren "
            "y conecta el pasado con el presente."
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
            "Carla graba con su hermano mayor un mensaje para la abuela que vive "
            "lejos. Preparan el micrófono en la sala y ensayan canciones que saben "
            "la harán sonreír. Entre toma y toma recuerdan veranos en la playa y "
            "cómo la abuela les enseñó a hacer cometas. El hermano ajusta el "
            "sonido mientras Carla escribe un guion con preguntas para que la "
            "abuela responda cuando escuche el audio. Al finalizar, envían el "
            "archivo y prometen llamarla por videoconferencia para ver su "
            "reacción. Descubren que su voz compartida puede acortar la distancia "
            "y reforzar el cariño familiar. Guardan un dibujo para enviárselo por "
            "correo y planean visitarla en verano para cantarle en persona."
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
