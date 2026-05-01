# Carry Regime Compass

Projet Python réalisé dans un contexte M1 Finance de Marché. L’objectif est de suivre, en temps quasi réel, si les grandes classes d’actifs rémunèrent correctement le risque porté par les stratégies de carry.

L’outil calcule un ratio **carry-to-volatility** sur FX, taux, crédit, actions et matières premières, puis en déduit un régime macro simple : **Risk-On**, **Mid-Cycle**, **Late-Cycle** ou **Deleveraging**. L’idée n’est pas de donner un signal de trading automatique, mais de fournir un tableau de bord lisible pour juger l’environnement de marché.

## Lancer le projet

```bash
pip install -e ".[dev]"
streamlit run carry_compass/viz/app.py
```

En local, si le script `streamlit` de l’environnement virtuel n’est pas disponible :

```bash
.venv/bin/python -m streamlit run carry_compass/viz/app.py
```

## Méthode

- Données : prix Yahoo Finance, normalisés puis stockés dans un cache SQLite.
- Carry : proxy annualisé en décimal, calculé séparément pour chaque classe d’actifs.
- Volatilité : volatilité réalisée 30 jours, annualisée.
- Ratio : carry divisé par volatilité réalisée, proche d’un Sharpe ex-ante simplifié.
- Régime : médiane cross-sectionnelle du carry et de la vol, puis z-score historique et classification.

## Architecture

- `config/` : univers de 26 tickers, paramètres et seuils de régime.
- `data/` et `cache/` : téléchargement, nettoyage yfinance, cache SQLite.
- `carry/` et `vol/` : calculs financiers par classe d’actifs.
- `regime/` : centroïde macro, classification, smoothing des transitions.
- `viz/` : interface Streamlit et graphiques Plotly.

## Limites connues

- FX : carry approximé par différentiels de taux directeurs, pas par vrais points de swap.
- Crédit : rendement ETF utilisé comme proxy, pas un vrai spread OAS.
- Actions : earnings yield basé sur P/E statique, pas sur prévisions point-in-time.
- Matières premières : proxies Yahoo faute de courbes futures complètes.
