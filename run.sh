#!/bin/bash
# Script de lancement du serveur MCP Narrations

set -e

# Couleurs pour les messages
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Démarrage du serveur MCP Narrations...${NC}"

# Vérifier si on est dans le bon répertoire
if [ ! -f "app/main.py" ]; then
    echo -e "${YELLOW}⚠️  Erreur: app/main.py non trouvé. Assurez-vous d'être à la racine du projet.${NC}"
    exit 1
fi

# Charger les variables d'environnement si .env existe
if [ -f ".env" ]; then
    echo -e "${GREEN}✓ Fichier .env trouvé${NC}"
else
    echo -e "${YELLOW}⚠️  Fichier .env non trouvé. Utilisation des valeurs par défaut.${NC}"
fi

# Vérifier si les dépendances sont installées
if ! python -c "import fastapi" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  FastAPI non trouvé. Installation des dépendances...${NC}"
    pip install -r requirements.txt
fi

# Lancer le serveur
# Option : démarrer un tunnel Cloudflare si demandé
if [ "${ENABLE_CLOUDFLARE_TUNNEL:-0}" = "1" ]; then
    TUNNEL_HOSTNAME="${TUNNEL_HOSTNAME:-mcp.numeniagen76.com}"
    TUNNEL_NAME="${TUNNEL_NAME:-mcp-narrations}"
    TARGET_URL="${TARGET_URL:-http://localhost:3333}"
    LOG_DIR="${LOG_DIR:-./logs}"
    mkdir -p "$LOG_DIR"

    if ! command -v cloudflared >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  cloudflared introuvable. Installe-le ou désactive ENABLE_CLOUDFLARE_TUNNEL.${NC}"
    else
        echo -e "${GREEN}✓ Tunnel Cloudflare activé (${TUNNEL_HOSTNAME} → ${TARGET_URL})${NC}"
        # lance le tunnel en arrière-plan, logs dans logs/tunnel.log
        TUNNEL_HOSTNAME="$TUNNEL_HOSTNAME" \
        TUNNEL_NAME="$TUNNEL_NAME" \
        TARGET_URL="$TARGET_URL" \
        nohup bash ./scripts/expose_cloudflare.sh > "$LOG_DIR/tunnel.log" 2>&1 &
        echo -e "${BLUE}🪄 Logs tunnel : $LOG_DIR/tunnel.log${NC}"
    fi
fi

echo -e "${GREEN}✓ Lancement du serveur sur http://0.0.0.0:3333${NC}"
echo -e "${BLUE}📖 Documentation disponible sur http://localhost:3333/docs${NC}"
echo ""

python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 3333 \
    --reload
