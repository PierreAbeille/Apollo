# Page Recommandations (`/recommandations`)

Le hub central pour découvrir des films, doté d'un puissant système de filtrage par humeur.

## 📍 Localisation
- `apps/web/src/app/recommandations/page.tsx` (Composant Serveur)

## 🔑 Fonctionnalités

### 1. Liste Unifiée
Par défaut, affiche les meilleurs films recommandés à l'utilisateur (Score de Goût / Taste Score) indépendamment du genre ou de l'humeur.
- **Source** : `movieService.getAllCandidatesPaginated`
- **Ordre par défaut** : Taste Score décroissant.

### 2. Filtrage par Humeur
Permet aux utilisateurs d'affiner les recommandations en fonction de leur état émotionnel actuel via le composant `GenreMoodFilter`.
- **Paramètres** : 
    - `mood` (ex: 'joy', 'fear')
    - `regulation` (valeur linéaire 0-100)
    - `intensity` ('plutot' | 'beaucoup')
- **Comportement** : Lorsqu'il est actif, la liste est reclassée par **Score de Correspondance Humeur** (Similarité Cosinus avec le vecteur cible) au lieu du Taste Score global.

### 3. Rendu Côté Serveur (SSR)
- **Zéro CLS** : Le HTML de la table est entièrement généré sur le serveur.
- **SEO Friendly** : Tout le contenu est indexable.
- **Performance** : La logique de filtrage lourde se produit sur le serveur (utilisant le JSON en mémoire), ne livrant que du HTML léger au client.

### 4. Feedback Visuel
- **Niche vs Public** : Des badges indiquent si un film est grand public ou une pépite cachée ("Niche").
- **Barres de Match** : Représentation visuelle du Taste Score.
- **Émotion Dominante** : Tooltip affichant l'émotion principale du film.

## 🔄 Flux de Données

1. **Requête** : L'utilisateur visite `/recommandations?mood=joy&regulation=50`.
2. **Serveur** : 
   - `page.tsx` parse les paramètres de recherche URL.
   - Appelle `getMovieService()`.
   - Appelle `getAllCandidatesPaginated(..., mood='joy', regulation=50)`.
   - Le service charge `movie_emotions.json`.
   - Le service calcule le vecteur cible (Target) (50% Joie + 50% Cible Régulation).
   - Le service classe à nouveau les candidats.
3. **Réponse** : Retourne le HTML avec la liste triée des films.
