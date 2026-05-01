# Carry Regime Compass

Projet réalisé dans le cadre du cours **Python for Finance** du M1 Finance de Marché à l’ESCP. L’objectif est de construire un outil quantitatif complet, lisible et maintenable, qui combine collecte de données, calculs financiers, classification de régime et visualisation interactive.

L’idée financière est simple : une stratégie de carry n’est attractive que si le rendement porté compense suffisamment le risque réalisé. Le dashboard mesure donc un ratio **carry-to-volatility** sur FX, taux, crédit, actions et matières premières, puis en déduit un régime macro simple : **Risk-On**, **Mid-Cycle**, **Late-Cycle** ou **Deleveraging**.

Le projet ne cherche pas à produire un signal de trading automatique. Il sert plutôt de tableau de bord macro : il permet de voir rapidement si le marché rémunère le risque de carry, si la volatilité devient dominante, et comment évolue le régime de marché.

## Lancer le projet

```bash
pip install -e ".[dev]"
streamlit run carry_compass/viz/app.py
```

En local, si le script `streamlit` de l’environnement virtuel n’est pas disponible :

```bash
.venv/bin/python -m streamlit run carry_compass/viz/app.py
```

## Ce que montre l'application

- Un scatter carry/vol par actif pour comparer le rendement porté au risque réalisé.
- Un classement des actifs par ratio carry-to-volatility, proche d’un Sharpe ex-ante simplifié.
- Un régime macro courant basé sur le centroïde cross-asset du marché.
- Une timeline des régimes récents pour visualiser les transitions.
- Une section methodology qui rend les hypothèses financières lisibles sans ouvrir le code.

## Méthode financière

- Données : prix Yahoo Finance, normalisés puis stockés dans un cache SQLite.
- Carry : proxy annualisé en décimal, calculé séparément pour chaque classe d’actifs.
- Volatilité : volatilité réalisée 30 jours, annualisée.
- Ratio : carry divisé par volatilité réalisée, proche d’un Sharpe ex-ante simplifié.
- Régime : médiane cross-sectionnelle du carry et de la vol, puis z-score historique et classification.

## Architecture Python

- `config/` : univers de 26 tickers, paramètres et seuils de régime.
- `data/` et `cache/` : téléchargement, nettoyage yfinance, cache SQLite.
- `carry/` et `vol/` : calculs financiers par classe d’actifs.
- `regime/` : centroïde macro, classification, smoothing des transitions.
- `viz/` : interface Streamlit et graphiques Plotly.
- `tests/` : tests unitaires sur les invariants financiers et les composants critiques.

## Limites connues

- FX : carry approximé par différentiels de taux directeurs, pas par vrais points de swap.
- Crédit : rendement ETF utilisé comme proxy, pas un vrai spread OAS.
- Actions : earnings yield basé sur P/E statique, pas sur prévisions point-in-time.
- Matières premières : proxies Yahoo faute de courbes futures complètes.
