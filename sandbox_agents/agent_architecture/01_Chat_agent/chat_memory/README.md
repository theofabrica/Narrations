# Chat memory des states

Ce dossier stocke les **states** produits par la couche 1 (chat).

## Regles de nommage
- Identifiant de state : `sNNNN` (ex: `s0001`, `s0002`, ...).
- A chaque nouvelle demande utilisateur, on cree un dossier :
  - `01_Chat_agent/chat_memory/sNNNN/`

## Contenu attendu
Dans chaque dossier de state :
- `state_01_abc.json` (state unique, rempli en 1a -> 1b -> 1c)

## Incrementation
Le compteur s'incremente a chaque **nouvelle interaction** utilisateur.
