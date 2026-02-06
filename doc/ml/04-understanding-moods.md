# Comprendre les Moods et l'IA Apollo

Ce guide explique comment Apollo "comprend" les émotions des films et comment fonctionne le système de filtrage par humeur.

## 1. La Roue des Émotions (Plutchik)

Pour qu'une IA comprenne les nuances émotionnelles d'un film, nous utilisons un modèle psychologique reconnu : la **Roue des Émotions de Robert Plutchik**.

Ce modèle postule qu'il existe 8 émotions primaires qui fonctionnent par paires opposées :
*   **Joie** ↔ **Tristesse**
*   **Confiance** ↔ **Dégoût**
*   **Peur** ↔ **Colère**
*   **Surprise** ↔ **Anticipation**

### Les Dyades (Mélanges)
Tout comme les couleurs primaires se mélangent (Bleu + Jaune = Vert), les émotions primaires se mélangent pour former des émotions complexes appelées **Dyades**.

Apollo est capable de détecter ces mélanges :
*   **Joie + Confiance = Amour** ❤️ (ex: *La La Land*)
*   **Peur + Surprise = Émerveillement** 🌟 (ex: *Interstellar*)
*   **Anticipation + Joie = Optimisme** 🌈 (ex: *Amélie Poulain*)

## 2. Comment l'IA "regarde" les films ?

Notre modèle de Machine Learning ne "regarde" pas le film image par image. Il analyse le film de manière sémantique en lisant :
*   Le synopsis détaillé
*   Les mots-clés associés
*   Les genres

Pour chaque film, l'IA attribue un score de 0 à 1 pour chacune des 8 émotions primaires.

> **Exemple pour "Vice-Versa" :**
> - Joie : 0.85 (Très élevé)
> - Tristesse : 0.70 (Élevé)
> - Peur : 0.10 (Faible)
> → C'est un film "Doux-Amer", un mélange complexe.

## 3. La Philosophie "Taste First"

Pourquoi ne pas juste chercher "Films joyeux" ? Parce que **le goût est subjectif, l'émotion est objective**.

*   *Objectivement*, "Les Tuche" est un film "Joyeux".
*   *Subjectivement*, si vous détestez l'humour populaire, vous détesterez ce film, même si vous voulez être joyeux.

C'est pourquoi Apollo fonctionne en deux temps :
1.  **D'abord, qui êtes-vous ?** L'IA sélectionne d'abord les 300 films qui correspondent le mieux à vos goûts cinématographiques profonds (Auteurs, style, complexité...).
2.  **Ensuite, comment allez-vous ?** Parmi ces 300 "pépites" potentielles, elle filtre celles qui correspondent à votre humeur du moment.

Cela garantit que **chaque recommandation est un bon film pour VOUS**, quelle que soit l'humeur.

## 4. Le Système de Percentiles (Relativité)

Comment définir ce qu'est un film "Triste" ?
*   La Liste de Schindler est "Triste" (10/10)
*   Titanic est "Triste" (8/10)
*   Spider-Man a des moments "Tristes" (3/10)

Si vous demandez un film triste, doit-on ne montrer que *La Liste de Schindler* ? Non.

Apollo utilise des **Percentiles**. Au lieu de dire "Montre-moi les films avec Tristesse > 0.8", on dit :
*"Parmi les films que j'aime, prends les 33% les plus tristes."*

Cela permet au système de s'adapter dynamiquement à votre sélection de films, qu'il s'agisse de blockbusters ou de films d'auteur.
