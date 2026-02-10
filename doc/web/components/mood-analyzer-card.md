# Composant MoodAnalyzerCard

Un composant de visualisation qui affiche le "Profil Émotionnel" d'un film.

## 📍 Localisation
`apps/web/src/components/recommendations/MoodAnalyzerCard.tsx`

## 🧠 Fonctionnalités
Ce composant prend les scores d'émotion d'un film (pré-calculés via ML) et affiche :
1.  **Émotion Dominante** : Le sentiment principal du film.
2.  **Dyades** : Combinaisons spéciales d'émotions (ex: Joie + Confiance = Amour).
3.  **Intensité** : La force de ces émotions par rapport à la moyenne.

## 🛠️ Utilisation
Utilisé principalement sur la **Page Détail du Film** (`/movie/[id]`) pour donner aux utilisateurs une compréhension rapide de l'ambiance du film sans spoilers.

```tsx
<MoodAnalyzerCard 
  tmdbId={12345} 
  title="Inception"
/>
```

Il récupère ses propres données côté client (ou peut recevoir des données initiales) pour garder le chargement de la page rapide.
