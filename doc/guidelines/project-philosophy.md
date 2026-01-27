# Philosophie du Projet Apollo

## 🎯 Vision

Apollo repense la découverte cinématographique en s'éloignant des algorithmes de recommandation traditionnels basés sur la popularité et les tags génériques. Notre mission est de **révéler les pépites** — ces films qui résonnent profondément avec tes goûts mais que tu n'aurais jamais trouvés seul.

### Pourquoi Apollo existe

Les plateformes mainstream (Netflix, Prime, etc.) optimisent pour l'**engagement** et le **temps de visionnage**. Leur objectif : te garder sur la plateforme. Apollo optimise pour la **pertinence sémantique** et la **découverte authentique**. Notre objectif : te faire découvrir des films qui te marquent.

**Problèmes résolus** :
- ❌ **Chambre d'écho algorithmique** : Netflix te recommande toujours le même type de contenu
- ❌ **Biais de popularité** : Les petits films excellents sont invisibles
- ❌ **Tags superficiels** : "Action, Drame" ne capture pas l'essence d'un film
- ❌ **Manque de transparence** : Pourquoi ce film m'est-il recommandé ?

---

## 🧠 Principes de Design

### 1. Sémantique > Tags

**Approche traditionnelle** :
```
Film: "Donnie Darko"
Tags: [Science-Fiction, Drame, Thriller]
→ Recommandation: Autres films avec ces mêmes tags
```

**Approche Apollo** :
```
Film: "Donnie Darko"
Embedding semantic: Analyse du synopsis, thèmes (adolescence, paradoxe temporel,
angoisse existentielle), ambiance (sombre, surréaliste), tone (mélancolique)
→ Recommandation: Films qui partagent cette "essence" même avec tags différents
```

**Principe** : Les embeddings capturent le **sens profond** plutôt que des catégories rigides.

### 2. Détection de Niche Automatique

Apollo identifie les films "sous le radar" en analysant :
- **Popularité TMDb** (< seuil)
- **Nombre de votes** (< seuil)
- **Ratio qualité/visibilité** (score élevé malgré faible popularité)

**Impact UX** :
- Thème visuel vert (`success`) pour les films niche
- Badge "Pépite Niche" explicite
- Priorisation dans les recommandations

**Pourquoi c'est important** : Les films niche ont souvent une "audience potentielle" beaucoup plus large que leur audience réelle. Apollo aide à combler ce gap.

### 3. Langue : FR pour UX, EN pour ML

**Décision critique** :
- **Interface utilisateur** : 100% français (labels, textes, navigation)
- **Données ML** : 100% anglais (synopsis, keywords, embeddings)

**Justification** :
1. **Qualité sémantique** : Les modèles d'embeddings sont mieux entraînés sur l'anglais
2. **Richesse TMDb** : Métadonnées anglaises plus complètes et précises
3. **Compatibilité modèle** : `paraphrase-multilingual-MiniLM-L12-v2` excelle sur l'anglais
4. **Hydratation flexible** : L'app web peut afficher le français via TMDb (langue `fr-FR`)

**Résultat** : Meilleure pertinence des recommandations sans compromettre l'expérience utilisateur.

### 4. Transparence Algorithmique

Chaque recommandation inclut :
- **Score de compatibilité** : Pourcentage explicite (similarité cosinus × 100)
- **Source de pertinence** : Basé sur ton profil utilisateur (films notés 8+)
- **Contexte** : Batch version, date de génération

**Pas de boîte noire** : L'utilisateur comprend pourquoi un film lui est suggéré.

### 5. Performance First

**Optimisations clés** :
- **DB-first filtering** : Filtrer les genres en mémoire depuis `movie_features` avant d'appeler TMDb
- **Batch processing** : Limiter les appels API concurrents (10 max)
- **Résumabilité** : Les pipelines ML skip les films déjà traités
- **Caching** : Embeddings sauvegardés en `.npy`, index en JSON

**Philosophie** : Ne jamais gaspiller une requête API. Privilégier PostgreSQL pour les opérations lourdes.

---

## 🏛️ Choix Techniques Fondamentaux

### Embeddings over Collaborative Filtering

**Pourquoi pas le filtrage collaboratif ?**
- Nécessite une large base d'utilisateurs (problème du "cold start")
- Biais vers les films populaires
- Ne capture pas la sémantique

**Pourquoi les embeddings ?**
- Fonctionne avec un **seul utilisateur** (toi)
- Comprend le **contexte et le sens** des films
- Modèles pré-entraînés disponibles (pas de training requis)

### PostgreSQL > Solutions NoSQL

- **Transactions ACID** : Garantie de cohérence des données
- **Upserts natifs** : `ON CONFLICT` pour éviter les doublons
- **Jointures efficaces** : Optimisation des requêtes multi-tables
- **Supabase** : Hosting PostgreSQL avec API REST auto-générée

### Next.js App Router > Pages Router

- **Server Components** : Réduction du JavaScript client
- **Streaming SSR** : Chargement progressif
- **Nested Layouts** : Meilleure réutilisabilité
- **Data Fetching** : Co-location avec les composants

---

## 🎨 Standards de Code

### TypeScript

- **Strict mode** : `"strict": true` dans `tsconfig.json`
- **Pas de `any`** : Typage explicite obligatoire
- **Interfaces > Types** : Pour les contrats de données
- **Server vs Client** : Composants clairement séparés

### Python

- **Type Hints** : Annotations pour tous les paramètres et retours
- **Docstrings** : Format Google style pour chaque fonction/classe
- **Error Handling** : Try/except avec logging explicite
- **Resumability** : Les scripts vérifient l'état de la DB avant de traiter

### Git

- **Commits atomiques** : Une fonctionnalité = un commit
- **Messages descriptifs** : Format `feat(scope): description 🎬`
- **Branching** : `main` pour production, feature branches pour développement

---

## 🔮 Évolutions Futures

### Court Terme
- [ ] Filtrage par "mood embeddings" (au-delà des genres)
- [ ] Export de listes personnalisées
- [ ] Détection automatique de nouvelles interactions Letterboxd

### Moyen Terme
- [ ] Multi-utilisateurs avec profils partagés
- [ ] Intégration Trakt.tv / IMDb
- [ ] Recommandations "anti-mainstream" explicites

### Long Terme
- [ ] Fine-tuning d'un modèle custom sur le corpus cinéma français
- [ ] Analyse de sentiment des critiques pour affiner les scores
- [ ] API publique pour développeurs tiers

---

## 💡 Principes de Contribution (Future)

Si ce projet devient open-source :
1. **Respect de la vision** : Privilégier la découverte sur l'engagement
2. **Documentation > Code** : Chaque PR doit inclure de la doc
3. **ML accessible** : Expliquer les concepts pour les juniors
4. **Performance** : Ne jamais régresser sur les optimisations existantes

---

## 📚 Références & Inspirations

- **Sentence-BERT** : Reimers & Gurevych (2019) - Embeddings de phrases
- **Cosine Similarity** : Standard pour comparaison sémantique
- **Letterboxd** : Philosophie de découverte cinématographique
- **The Movie Database (TMDb)** : API ouverte et communautaire
