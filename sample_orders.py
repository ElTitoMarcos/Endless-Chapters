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
                'Ana y su gato Ori\u00f3n se internan en un bosque donde '
                'luci\u00e9rnagas iluminan \u00e1rboles que susurran secretos. '
                'Siguen un sendero de piedras brillantes y hallan una '
                'cascada que concede deseos a quienes creen.'
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
                'Mateo recibe el encargo de encender el viejo faro de su '
                'abuelo ante una tormenta. Con su perro Foco, sube '
                'escalones gastados, limpia el cristal salado y logra que '
                'la luz gu\u00ede a los barcos perdidos.'
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
                'Carla descubre en el \u00e1tico de su abuela un libro '
                'cubierto de polvo. Al abrirlo, las palabras se elevan como '
                'chispas y la llevan junto a su mam\u00e1 a mares de nubes '
                'donde cada decisi\u00f3n cambia la aventura.'
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

