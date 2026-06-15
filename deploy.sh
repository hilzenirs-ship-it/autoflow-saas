#!/bin/bash

# AutoFlow SaaS - Deploy Script
# Uso: ./deploy.sh [docker|heroku|railway]

set -e

DEPLOY_TYPE=${1:-docker}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 AutoFlow SaaS Deployment Script"
echo "=================================="
echo ""

# Validar .env existe
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo "⚠️  Arquivo .env não encontrado!"
    echo "📋 Criando .env.example como template..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
    echo "✏️  Edite .env com suas credenciais e execute novamente"
    exit 1
fi

case $DEPLOY_TYPE in
    docker)
        echo "🐳 Deploying with Docker Compose..."
        docker-compose down || true
        docker-compose up --build -d
        echo "✅ Docker deployment concluído!"
        echo "🌐 Acesse: http://localhost:5000"
        echo "📊 Logs: docker-compose logs -f app"
        ;;
    
    heroku)
        echo "🌩️  Deploying to Heroku..."
        
        if ! command -v heroku &> /dev/null; then
            echo "❌ Heroku CLI não encontrado. Instale em: https://devcenter.heroku.com/articles/heroku-cli"
            exit 1
        fi
        
        APP_NAME="autoflow-$(date +%s)"
        echo "📝 Criando app Heroku: $APP_NAME"
        
        heroku create "$APP_NAME"
        heroku addons:create heroku-redis:premium-0 -a "$APP_NAME"
        
        echo "🔐 Configurando variáveis de ambiente..."
        heroku config:set \
            FLASK_ENV=production \
            DEBUG=False \
            SECRET_KEY="$(openssl rand -hex 32)" \
            DATABASE_PATH=/app/database/hilflow.db \
            -a "$APP_NAME"
        
        echo "📤 Fazendo push..."
        git push heroku main
        
        echo "✅ Heroku deployment concluído!"
        echo "🌐 Acesse: https://$APP_NAME.herokuapp.com"
        echo "📊 Logs: heroku logs -f -a $APP_NAME"
        ;;
    
    railway)
        echo "🚀 Deploying to Railway..."
        echo "📍 Visite: https://railway.app"
        echo "1. Conecte sua conta GitHub"
        echo "2. Selecione este repositório"
        echo "3. Configure as variáveis de ambiente"
        echo "4. Railway fará deploy automático!"
        ;;
    
    *)
        echo "❌ Tipo de deploy inválido: $DEPLOY_TYPE"
        echo "Opções: docker, heroku, railway"
        exit 1
        ;;
esac

echo ""
echo "✨ Deploy iniciado com sucesso!"
