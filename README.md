# Veille Emploi Casablanca

PWA personnelle en français pour Android/Chrome. Hébergement statique GitHub Pages, collecte Python sur GitHub Actions, stockage public minimal dans `data/jobs.json`, favoris et statut « consultée » gardés localement sur chaque appareil.

## Ce qui est réellement automatisé
- API publique Jobicy, en respectant l'obligation de conserver le lien source et le nom Jobicy. Le résultat public est limité aux offres dont la géographie indique une portée mondiale/régionale ou le Maroc.
- Flux RSS explicitement autorisés, si vous en ajoutez dans `config.json`.
- Déduplication par URL, conservation de la date de première détection, historique jusqu'à 120 jours, journal des erreurs.
- Planification quotidienne à 07:17 UTC via GitHub Actions; lancement manuel possible depuis l'onglet Actions.

## Limites importantes
- Ce projet ne collecte PAS automatiquement les pages HTML de LinkedIn Jobs ou Indeed, ne contourne aucun login/CAPTCHA et n'utilise pas Google Jobs comme API (il n'existe pas d'API publique générale Google Jobs). Pour ces plateformes, configurez leurs alertes officielles par e-mail et utilisez leurs pages de recherche. Ne copiez un flux RSS que si la source le propose/autorise.
- L'API Jobicy vise les offres à distance et ne remplace pas les annonces locales Casablanca. Les flux RSS configurés sont nécessaires pour augmenter la couverture locale. Le filtrage géographique est heuristique et peut manquer des annonces.
- GitHub Pages nécessite un dépôt public sur GitHub Free. Le fichier `data/jobs.json` est public; n'y mettez aucune donnée personnelle. Les favoris et les offres consultées restent dans le stockage local du navigateur et ne sont pas synchronisés.
- Les tâches planifiées GitHub peuvent être retardées, désactivées après 60 jours d'inactivité d'un dépôt public, ou échouer si la source est indisponible. Contrôlez l'onglet Actions de temps en temps.
- Le navigateur ne peut pas garantir la mise à jour quotidienne si l'automatisation serveur est désactivée. L'actualisation dans l'app relit les données publiées, elle ne lance pas elle-même la collecte.

## Déploiement depuis le téléphone
1. Connectez-vous à GitHub dans Chrome et créez un dépôt **public** nommé `veille-emploi-casablanca`.
2. Téléversez les fichiers et dossiers de cette archive en conservant leur structure. L'interface GitHub web permet d'ajouter des fichiers; pour une première installation, le plus simple est de téléverser l'archive décompressée depuis un gestionnaire de fichiers ou d'utiliser l'éditeur web GitHub. Ne publiez pas de jeton ou de secret.
3. Ouvrez **Settings → Pages**, choisissez **Deploy from a branch**, branche `main`, dossier `/(root)`, puis **Save**.
4. Ouvrez **Actions → Collecte quotidienne des offres**. Si GitHub demande une autorisation, activez les workflows. Lancez **Run workflow** une fois. Vérifiez que `data/jobs.json` a été mis à jour et que l'exécution est verte.
5. Ouvrez l'adresse Pages affichée dans Settings → Pages. Dans Chrome Android, menu ⋮ → **Ajouter à l'écran d'accueil** ou **Installer l'application**.

## Ajouter un flux RSS autorisé
Dans `config.json`, ajoutez un objet à `rss_feeds`, par exemple (exemple fictif de configuration, pas un flux réel):
```json
{
  "name": "Nom de la source",
  "url": "https://exemple.org/flux-rss-offres.xml",
  "company": "",
  "location": "Casablanca Maroc"
}
```
Ne laissez pas l'URL fictive dans la configuration. La source doit réellement proposer ce flux et autoriser son utilisation. `company` et `location` sont des valeurs de contexte pour ce flux; ne les utilisez que si elles s'appliquent à toutes ses annonces.

## Tester localement
Python 3.10+ : `python -m unittest discover -s tests -v` puis `python collect.py`. La collecte réelle nécessite un accès Internet. Les tests unitaires n'utilisent pas d'annonces réelles et ne les injectent pas dans l'application.
