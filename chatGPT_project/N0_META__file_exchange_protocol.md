diff --git a/chatGPT_project/N0_META__file_exchange_protocol.md b/chatGPT_project/N0_META__file_exchange_protocol.md
index 1d9a0a68b1ac49bc550d1276e55d8610fb635a42..bc482421ffb9792c0f25fcce44e5ff0bb8ec15da 100644
--- a/chatGPT_project/N0_META__file_exchange_protocol.md
+++ b/chatGPT_project/N0_META__file_exchange_protocol.md
@@ -45,64 +45,68 @@
 - Champs obligatoires : `version`, `kind`, `action`, `id`, `ts`, `payload`.
 - Champs recommandés : `from`, `meta.project`.
 - Champs optionnels : `meta.user`, `meta.checksum`, tout champ additionnel nécessaire à l’action.
 
 ## Schéma JSON minimal (retour / ACK)
 ```json
 {
   "version": "1.0",
   "kind": "ACK",
   "action": "pipeline_audio_stack",
   "id": "req001",
   "ts": "2026-01-08T14:21:30Z",
   "from": "local_app",
   "status": "done",
   "result": {
     "links": ["https://.../audio1.mp3"],
     "job_id": "job-xyz"
   },
   "error": null
 }
 ```
 - `status` : `done` ou `error`.
 - `error` : null ou objet `{ "code": "...", "message": "...", "retryable": false }`.
 
 ## Règles côté ChatGPT (production du fichier)
+- **Obligation de production** : si une action serveur est demandée (image/vidéo/audio/pipeline), l’agent **doit produire immédiatement** un fichier JSON conforme, **sans demander d’autorisation**.
+- **Sortie attendue** : présenter un **fichier prêt à télécharger** avec :
+  1) le **nom exact du fichier** (nomenclature),
+  2) le **contenu JSON** complet.
+- **Interdiction** : ne pas fournir “juste un extrait” ou un JSON “à copier/coller”. Le format doit être explicitement livré comme **fichier à enregistrer**.
 - Respecter strictement la nomenclature du nom de fichier et le schéma.
 - Ne jamais inclure de secrets ou de tokens.
 - Préférer des payloads courts et explicites ; si des assets sont requis, référencer des URLs déjà publiques ou fournir des instructions de récupération.
 - Toujours inclure `version` (actuelle : `1.0`).
 
 ## Règles côté routine locale
 - Surveiller le dossier de téléchargements utilisateur.
 - Filtrer uniquement les fichiers qui matchent `NARR_*.json`.
 - Valider le JSON (structure minimale + `kind/action/id/ts/payload`).
 - Déplacer le fichier validé dans un répertoire “spool” local (ex. `~/narrations_spool/inbox/`).
 - Transmettre le contenu au serveur via l’endpoint HTTP exposé derrière Cloudflare (POST `/mcp` ou endpoint dédié si différent).
 - Enregistrer la réponse dans `~/narrations_spool/outbox/` en respectant la nomenclature `NARR_ACK_<ACTION>_<ID>_<TS>.json`.
 - Option : supprimer ou archiver le fichier d’origine après traitement réussi.
 
 ## Sécurité & résilience
 - Aucun secret ne transite dans les JSON générés par ChatGPT.
 - Si un chiffrement est nécessaire, seul le côté local devrait chiffrer/déchiffrer (clé non partagée avec ChatGPT).
 - Idempotence : la routine locale doit ignorer un fichier dont l’`id` a déjà été traité et loguer les doublons.
 - Journalisation minimale : consigner les événements (détection, validation, envoi, retour, erreur).
 - En cas d’échec réseau, réessayer avec backoff ou placer le fichier en `spool/retry/`.
 
 ## Évolutions de version
 - `version` du schéma suit `MAJOR.MINOR`.
 - Incrémenter `MINOR` pour des ajouts rétro-compatibles, `MAJOR` pour des ruptures.
 - La routine locale doit refuser poliment une version inconnue ou supérieure (log + éventuellement message d’erreur en retour).
 
 ## Bonnes pratiques pour ACTION/PAYLOAD
 - `action` doit être stable et documenté (ex. `pipeline_audio_stack`, `elevenlabs_voice`, `higgsfield_video`).
 - `payload` doit contenir uniquement les paramètres nécessaires à l’action (limiter la taille).
 - Inclure un champ `wait_for_completion` si l’action est asynchrone et que l’appelant veut attendre ou non.
 - Pour le suivi, inclure `trace` ou `meta` avec `project`, `session`, `requester`.
 
 ## Résumé du flux
 1) ChatGPT génère un fichier de commande : `NARR_CMD_<ACTION>_<ID>_<TS>.json`.
 2) L’utilisateur le télécharge ; il arrive dans le dossier de téléchargements.
 3) La routine locale le détecte, le valide, le déplace en “spool”, l’envoie au serveur.
 4) Le serveur répond ; la routine écrit un fichier ACK : `NARR_ACK_<ACTION>_<ID>_<TS>.json`.
 5) ChatGPT peut consommer le contenu de l’ACK si l’utilisateur le lui fournit (copier-coller ou re-téléversement).
-
