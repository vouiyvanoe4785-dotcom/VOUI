from decimal import ROUND_HALF_UP, Decimal

from num2words import num2words

CURRENCY_WORDS = {
    "MAD": ("dirham", "dirhams", "centime", "centimes"),
    "EUR": ("euro", "euros", "centime", "centimes"),
    "USD": ("dollar", "dollars", "cent", "cents"),
}


def montant_en_lettres(montant, devise="MAD"):
    """'1250.50' -> 'mille deux cent cinquante dirhams et cinquante centimes'."""
    montant = Decimal(montant or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negatif = montant < 0
    montant = abs(montant)
    unites = int(montant)
    centimes = int((montant - unites) * 100)

    sing, plur, c_sing, c_plur = CURRENCY_WORDS.get(devise, (devise, devise, "centime", "centimes"))
    # "un million de dirhams", mais "un million deux cents dirhams".
    liaison = " de" if unites and unites % 1_000_000 == 0 else ""
    texte = f"{num2words(unites, lang='fr')}{liaison} {sing if unites <= 1 else plur}"
    if centimes:
        texte += f" et {num2words(centimes, lang='fr')} {c_sing if centimes == 1 else c_plur}"
    if negatif:
        texte = f"moins {texte}"
    return texte
