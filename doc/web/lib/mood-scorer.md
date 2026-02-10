# Librairie Mood Scorer

Logique centrale pour la gestion des vecteurs d'émotion, le calcul des cibles et le classement des films.

## 📍 Localisation
`apps/web/src/lib/mood-scorer.ts`

## 🧠 Concepts

### 1. Espace Vectoriel
Basé sur la Roue des Émotions de Plutchik.
- **8 Émotions Primaires** : Joie, Confiance, Peur, Surprise, Tristesse, Dégoût, Colère, Anticipation.
- **Dyades** : Combinaison de 2 émotions primaires adjacentes (ex: Joie + Confiance = Amour).

### 2. Matrices de Transformation
Définit comment les humeurs sélectionnées se traduisent en vecteurs cibles.

- **Congruence (`T_CONGRUENCE`)** : Matrice identité. 
  - *Utilisateur sélectionne* : Joie
  - *Système cible* : Joie (1.0)
  
- **Régulation (`T_REGULATION`)** : Matrice d'opposition.
  - *Utilisateur sélectionne* : Tristesse
  - *Système cible* : Joie (0.6) + Confiance (0.4) (Antidote)

### 3. Interpolation
La valeur du slider utilisateur (0-100) est normalisée en un facteur $f \in [0, 1]$.
Le vecteur cible $V_{target}$ est calculé comme suit :

$$ V_{target} = f \times V_{regulation} + (1-f) \times V_{congruence} $$

Cela permet un mélange fluide entre "Trouver des films qui correspondent à mon humeur" et "Trouver des films qui changent mon humeur".

## 🛠️ Fonctions Clés

### `getInterpolatedTarget(mood: Mood, factor: number): number[]`
Retourne le vecteur cible à 8 dimensions basé sur l'humeur sélectionnée et le facteur de régulation.

### `rerankWithMood(candidates, emotionData, mood, regulation)`
1. **Filtrer** : Garde les candidats où le vecteur de l'émotion dominante du film a une similarité cosinus > 0 avec le vecteur cible.
2. **Scorer** : Calcule la similarité cosinus entre le vecteur du film et le vecteur cible.
3. **Trier** : Trie par ce score de similarité (décroissant).

### `getDyadFromPrimaries(p1, p2)`
Helper pour identifier si deux émotions primaires sélectionnées forment une dyade de Plutchik valide. Retourne le nom de la dyade (ex: 'love') ou `null`.
