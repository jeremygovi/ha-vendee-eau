# Vendée Eau pour Home Assistant

Intégration personnalisée Home Assistant pour le portail client Vendée Eau.

> Projet non officiel. Cette intégration n'est pas affiliée à Vendée Eau.

## Fonctionnalités

- Authentification au portail client Vendée Eau.
- Découverte automatique des identifiants techniques nécessaires aux appels du
  portail.
- Récupération de l'historique officiel de consommation exposé par Vendée Eau.
- Capteurs Home Assistant pour la dernière consommation, sa date, le total et le
  nombre de points disponibles.
- Diagnostics Home Assistant sans exposition du mot de passe.

Le portail ne semble pas exposer une consommation mensuelle détaillée. Cette
intégration utilise donc uniquement les relevés officiels disponibles.

## Installation avec HACS

Cette intégration n'est pas encore publiée dans la liste par défaut HACS. Elle
peut être installée comme dépôt personnalisé.

1. Ouvrez HACS dans Home Assistant.
2. Allez dans `Intégrations`.
3. Ouvrez le menu `...` puis `Dépôts personnalisés`.
4. Ajoutez l'URL du dépôt :

```text
https://github.com/jeremygovi/ha-vendee-eau
```

5. Sélectionnez la catégorie `Integration`.
6. Cliquez sur `Ajouter`, puis installez `Vendee Eau`.
7. Redémarrez Home Assistant.

Ajoutez ensuite l'intégration depuis :

```text
Paramètres > Appareils et services > Ajouter une intégration > Vendee Eau
```

## Installation manuelle

Copiez le dossier `custom_components/vendee_eau` dans le dossier
`custom_components` de votre installation Home Assistant, puis redémarrez Home
Assistant.

Exemple avec `rsync` :

```bash
rsync -av --delete \
  custom_components/vendee_eau/ \
  user@homeassistant.local:/homeassistant/custom_components/vendee_eau/
```

## Configuration

L'intégration demande uniquement :

- identifiant Vendée Eau ;
- mot de passe Vendée Eau.

Les identifiants techniques `abonnement_id`, `point_installation_id` et
`equipement_id` sont découverts automatiquement après connexion.

## Entités

Les entités exposées actuellement sont :

- `Identifiant abonnement` ;
- `Identifiant point d'installation` ;
- `Identifiant équipement` ;
- `Dernière consommation` ;
- `Date dernière consommation` ;
- `Points de consommation` ;
- `Total consommation`.

L'historique de consommation est aussi disponible en attribut sur le capteur
`Dernière consommation`.

## Limites connues

- Les données dépendent du portail Vendée Eau, qui peut changer sans préavis.
- La consommation est celle fournie par le graphique officiel du portail.
- Les factures et documents ne sont pas encore exposés dans Home Assistant.

## Développement

Installez les dépendances utiles aux tests :

```bash
python3 -m pip install --user -r requirements-dev.txt
```

Lancez les vérifications locales :

```bash
make check
```

`make check` compile les fichiers Python et lance les tests.

## Confidentialité

Ne publiez jamais de logs Home Assistant complets sans les relire. Le portail
peut contenir des données personnelles : nom, adresse, numéro de contrat,
factures ou informations de compteur.

Les diagnostics Home Assistant masquent l'identifiant et le mot de passe.

## Logo et marques

Le logo utilisé comme icône de l'intégration provient du site public de Vendée
Eau. Vendée Eau et son logo restent la propriété de leurs ayants droit.
