#!/bin/bash

echo "🔄 Mise à jour du planning vers GitHub..."

# On ajoute tous les fichiers nécessaires
git add planning.html dashboard.html planning.csv membres.csv taches.csv competences.csv

# On crée le commit avec la date du jour
git commit -m "Mise à jour automatique : $(date '+%Y-%m-%d %H:%M')"

# On envoie vers GitHub (branche main)
git push origin main

echo "✅ Le planning est en ligne !"