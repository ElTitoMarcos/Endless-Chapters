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
                'Cada domingo Ana hornea pan con su abuela Rosa. Al amasar '
                'recuerdan al abuelo pescador, y la casa se llena de '
                'historias y risas que enseñan a la pequeña la fuerza de la '
                'familia y el amor que perdura.'
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
                'Mateo organiza una cena sorpresa para el aniversario de '
                'sus padres. Entre recetas heredadas y fotos antiguas, '
                'descubre cómo el esfuerzo compartido mantiene unida a la '
                'familia y honra su historia.'
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
                'Carla y su mamá pasan la Navidad decorando la casa con '
                'adornos hechos a mano. Cada esfera trae recuerdos de '
                'viajes y canciones, y juntas comprenden que la verdadera '
                'magia está en compartir tiempo y cariño.'
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

