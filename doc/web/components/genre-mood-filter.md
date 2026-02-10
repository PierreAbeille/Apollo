# Composant GenreMoodFilter

L'interface principale permettant aux utilisateurs de filtrer les recommandations en fonction de leur état émotionnel souhaité.

## Fonctionnalités
- **Sélection de l'Humeur** : Les utilisateurs peuvent sélectionner 1 ou 2 émotions primaires à partir d'une grille de 8 cartes.
- **Logique des Dyades** :
  - Sélectionner 2 émotions adjacentes forme une "Dyade" (ex: Joie + Confiance = Amour).
  - Les émotions non adjacentes sont désactivées pour forcer des dyades de Plutchik valides.
- **Slider de Régulation (0-100)** :
  - Contrôle la stratégie de "Régulation", mélangeant deux vecteurs cibles :
    - **0 (Congruence)** : Trouve des films correspondant à l'humeur sélectionnée.
    - **100 (Régulation)** : Trouve des films qui fournissent l'*antidote* à l'humeur sélectionnée (ex: Tristesse -> Joie).
  - Utilise une interpolation linéaire pour calculer un vecteur cible pondéré.
- **Toggle d'Intensité** : Filtre les films selon la force de leur correspondance avec l'humeur cible (Top 33% vs Top 66%).

## Implémentation Technique

### Réactivité & État
- **État Local** : `useState` est utilisé pour le slider et le toggle afin d'assurer une réactivité à 60fps.
- **Debouncing** : `useDebounce` (300ms) empêche de spammer l'URL/Router à chaque pixel de mouvement du slider.
- **Synchro URL** : La source de vérité reste les paramètres de requête de l'URL (`mood`, `regulation`, `intensity`), assurant le partage des liens.

### Animations
- **Framer Motion** :
  - La prop `layout` gère le réordonnancement/mise à l'échelle fluide de la grille.
  - `AnimatePresence` gère l'entrée/sortie de la barre d'outils.
  - `motion.div` pilote les micro-interactions (effets de survol, tap).

### Fichiers Clés
- `src/components/recommendations/GenreMoodFilter.tsx` : Composant UI principal.
- `src/lib/mood-scorer.ts` : Logique centrale pour les calculs vectoriels, l'interpolation et le scoring.
