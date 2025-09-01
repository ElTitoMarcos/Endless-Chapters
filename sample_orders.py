from __future__ import annotations

from datetime import datetime
import uuid


def get_sample_orders() -> list[dict]:
    """Return a small set of sample orders covering different options."""
    samples = [
        {
            'order': '1001',
            'client': 'Ana',
            'email': 'ana@example.com',
            'cover': 'Premium Hardcover',
            'personalized_characters': 0,
            'narration': 'Narrated by your loved one',
            'revisions': 0,
            'tags': ['qr', 'voice', 'qr_audio'],
            'voice_name': 'Luz',
            'voice_seed': 'abc123',
            'voice_text': 'Hola, este es tu audiolibro...',
            'story': (
                'Cada domingo Ana hornea pan con su abuela Rosa. Mientras amasan, '
                'cantan boleros y recuerdan al abuelo pescador que les enseñó a '
                'reconocer el viento. La noche trae la luna que la abuela jura '
                'hace el pan más esponjoso. La niña guarda las recetas en una '
                'caja de madera y sueña con enseñárselas algún día a sus hijos, '
                'para que también sientan en el aire el olor a hogar y la fuerza '
                'de la familia que nunca se quiebra. Cuando el pan está listo lo '
                'reparten entre los vecinos y la abuela dice que cada hogaza lleva '
                'un deseo secreto. Ana cierra los ojos, huele la corteza tostada y '
                'promete cuidar esa tradición incluso cuando la vida la lleve lejos.'
            )
        },
        {
            'order': '1002',
            'client': 'Ben',
            'email': 'ben@example.com',
            'cover': 'Standard Hardcover',
            'personalized_characters': 1,
            'narration': 'None',
            'revisions': 1,
            'tags': ['voice'],
            'voice_name': 'Carlos',
            'voice_text': 'Este es un mensaje sin QR.',
            'story': (
                'Durante semanas ahorra su mesada para comprar velas de vainilla y '
                'enmarcar una foto de la boda. Mateo organiza una cena sorpresa '
                'para el aniversario de sus padres. Empieza revisando el cuaderno '
                'de recetas de la abuela, donde cada anotación tiene manchas de '
                'salsa y fechas de fiesta. Llama a sus tíos para pedir prestada la '
                'mesa grande y a sus primos para que traigan flores del jardín '
                'comunitario. Mientras hierve el caldo, escucha la historia de '
                'cómo sus padres se conocieron en un baile de barrio y decide '
                'recrear la misma canción. Al final, cuando apagan las velas, todos '
                'reconocen que el esfuerzo compartido ha cosido aún más la tela de '
                'la familia.'
            ),
            'character_names': ['Mateo']
        },
        {
            'order': '1003',
            'client': 'Carla',
            'email': 'carla@example.com',
            'cover': 'Premium Hardcover',
            'personalized_characters': 2,
            'narration': 'Narrated by your loved one',
            'revisions': 2,
            'tags': ['qr'],
            'story': (
                'Carla y su mamá se preparan para Navidad decorando la casa con '
                'adornos caseros. Recortan estrellas de cartón, enhebran hilos '
                'dorados y pegan fotos de la familia en cada esfera del árbol. Al '
                'abrir una caja antigua aparece la carta que el abuelo escribía cada '
                'diciembre desde el mar, y Carla insiste en leerla en voz alta. '
                'Después preparan chocolate caliente y se sientan en la alfombra a '
                'escuchar villancicos que su abuela solía cantar. Comprenden que la '
                'verdadera magia de la temporada está en volver a encontrarse y '
                'agradecer juntos todo lo vivido. Esa noche prometen seguir la '
                'tradición para que las nuevas generaciones no olviden de dónde '
                'vienen.'
            ),
            'character_names': ['Carla', 'Mamá']
        }
    ]
    for s in samples:
        s.setdefault('voice_name', '')
        s.setdefault('voice_seed', '')
        s.setdefault('voice_text', '')
        s.setdefault('personalized_characters', 0)
        s.setdefault('narration', 'None')
        s.setdefault('revisions', 0)
        s.setdefault('story', '')
        s.setdefault('character_names', [])
        s['id'] = str(uuid.uuid4())
        s['created'] = str(datetime.now().date())
    return samples

