# AGENTS.md

## Project: Baromètre CERENE Saussure

Le Baromètre est un outil éducatif réel utilisé au CERENE Saussure pour le suivi comportemental.

### Philosophy
- Ce n’est pas un système punitif.
- Il sert à structurer des observations, repérer des tendances, soutenir un suivi juste, améliorer la cohérence entre adultes et faciliter la communication avec les familles et les équipes.
- Il évalue des comportements et des situations, pas la valeur d’un élève.

### Current priority
Le produit fonctionne déjà bien.
L’objectif n’est pas de le réinventer, mais de supprimer une friction opérationnelle importante.

### Current flow
QR code -> Google Form -> Google Sheet -> export CSV manuel -> upload manuel dans Streamlit

### Target flow
QR code -> Google Form -> Google Sheet privé -> Streamlit connecté directement -> rafraîchissement automatique

### Non-negotiable rules
- Ne pas transformer l’outil en système punitif.
- Ne pas changer la logique pédagogique sans instruction explicite.
- Ne pas modifier le sens des couleurs.
- Ne pas casser la traçabilité.
- Préférer des changements minimaux, lisibles et robustes.

### Technical guidance
- Conserver autant que possible l’UI actuelle et les onglets existants.
- Priorité à la fiabilité et à la clarté.
- Éviter la sur-ingénierie.
- Ajouter une connexion privée Google Sheets via Streamlit.
- Préserver le système de connexion actuel pour l’instant.
- Ne pas ajouter d’IA à cette étape.

### Important known issue
- Vérifier et corriger la logique de calcul de période (`get_p()`), qui contient probablement un bug.