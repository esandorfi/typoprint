"""Fictional bilingual content shared by layout conformance and visual previews."""

from typoprint import Chapter as MarkdownDocument
from typoprint import Document as PreparedDocument

FRENCH_PARAGRAPH = (
    "Dans cet atelier fictif, une équipe observe une machine avant de modifier son "
    "réglage. Elle compare les mesures : un délai plus court réduit l’attente, mais "
    "augmente les reprises. « Mesurer avant de conclure » reste son principe ; "
    "aucune valeur ne décrit une installation réelle. La vérification conserve "
    "l’origine de chaque observation et explique les incertitudes."
)
ENGLISH_PARAGRAPH = (
    "In this fictional workshop, an engineer compares two bounded retry policies. "
    "A shorter delay improves response time while increasing repeated work. "
    "The report records the assumptions, the observed limits and the next "
    "measurement. Its conclusion remains provisional until the experiment can "
    "be repeated under the same conditions."
)


def specimen() -> PreparedDocument:
    return PreparedDocument(
        chapters=(
            MarkdownDocument(
                name="fictional/atelier.md",
                markdown="""---
title: "Un atelier fictif"
subtitle: "Mesures et compromis — Fictional engineering report"
author: "Équipe fictive"
date: "2026-10-26"
version: "1.0"
---

## Mesures et hypothèses

Un texte **en gras**, *en italique* et ***en gras italique***, avec une note.[^note]
Voir [les résultats](results.md#results) et [la référence externe](https://example.org/reference).

> Une conclusion provisoire : conserver les hypothèses et vérifier les limites.

| Politique | Délai | Limite observée |
| --- | --- | --- |
| Patiente | 100 ms | Réponse plus lente |
| Rapide | 20 ms | Davantage de reprises |
| Bornée | 50 ms | Nombre maximal explicite |

```python
def retry(delay_ms: int) -> str:
    return "code : inchangé / unchanged"
```

```mermaid
flowchart LR
 A[Mesurer] --> B[Comparer]
 B --> C[Décider]
```

### Lecture longue

"""
                + "\n\n".join([FRENCH_PARAGRAPH] * 12)
                + "\n\n[^note]: Note fictive : une mesure ne suffit pas à établir une règle.\n",
            ),
            MarkdownDocument(
                name="fictional/results.md",
                markdown="""# Results

## Measurements and limits

See [the workshop](atelier.md#mesures-et-hypothèses).

"""
                + "\n\n".join([ENGLISH_PARAGRAPH] * 10)
                + "\n\nEnd of the fictional specimen.\n",
            ),
        )
    )
