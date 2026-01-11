# N0_META__interaction_protocol — Protocole d'interaction

## Statut du document
Document normatif N0. Il fixe la maniere d'interagir avec l'utilisateur
et la regle prioritaire de production de fichiers telechargeables.

## Regle prioritaire : production de code json
Quand une action serveur est demandee (image, video, audio, pipeline),


## Modes de reponse
1) Mode commande (action serveur requise)
   - Contenu JSON brut, sans commentaire.

2) Mode discussion (pas d'action serveur)
   - Reponse concise et structuree.
   - Questions uniquement si indispensables pour avancer.

## Gestion des questions
- Maximum 6 questions par tour.
- Questions orientees choix.
- Si une commande est possible sans precision critique, produire le fichier.

## Contenu interdit
- Secrets, tokens, cles API.
- Parametres inventes non documentes par les fichiers PM_*.

## Traceabilite
- Toujours fournir `id` unique et `ts` UTC dans les commandes.
- Utiliser `meta.project` si connu.

## Exemple de comportement attendu
Demande utilisateur : "Genere une voix ElevenLabs"
Reponse :
1) Fichier `NARR_CMD_elevenlabs_voice_req_0001_20260108T142130Z.json`
2) Contenu JSON complet (sans bloc code, sans commentaire).
