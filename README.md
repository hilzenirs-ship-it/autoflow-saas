# AutoFlow

SaaS Flask + SQLite para CRM, atendimento, automacao, agendamentos, fluxos, webhooks e limites de plano.

## Producao

Para producao, use Gunicorn via `wsgi.py`. Nao suba producao com `python app.py`.

```bash
gunicorn -w 3 -b 0.0.0.0:${PORT:-5000} wsgi:app
```

Variaveis obrigatorias/recomendadas:

- `FLASK_ENV=production`
- `DEBUG=False`
- `SECRET_KEY` forte, unica e secreta
- `DATABASE_PATH` apontando para o SQLite persistente
- `REDIS_URL` ou `RATELIMIT_STORAGE_URI` para rate limit compartilhado
- `CACHE_REDIS_URL` para cache compartilhado em producao
- `SESSION_COOKIE_SECURE=True` quando estiver usando HTTPS
- `META_APP_SECRET` para validar assinatura dos webhooks Meta
- `MERCADO_PAGO_WEBHOOK_SECRET`
- `MERCADO_PAGO_API_KEY`

Em producao, o app falha ao iniciar se:

- `SECRET_KEY` estiver ausente, curta ou fraca
- `DEBUG=True`
- `REDIS_URL`/`RATELIMIT_STORAGE_URI` nao estiver configurado para o rate limit

O healthcheck publico fica em:

```text
GET /healthz
```

Ele retorna apenas o estado basico do app e banco.

## Docker

O Dockerfile inicia o app com Gunicorn e possui `HEALTHCHECK`.

```bash
docker-compose up --build
```

No Docker Compose atual, Redis ja esta configurado para rate limit:

```text
REDIS_URL=redis://redis:6379/0
RATELIMIT_STORAGE_URI=redis://redis:6379/0
CACHE_REDIS_URL=redis://redis:6379/0
```

## Banco

O app usa SQLite nesta fase para manter compatibilidade.

Por padrao local, sem `DATABASE_PATH`, o codigo preserva o banco legado `banco.db`. Quando `DATABASE_PATH` e definido, ele passa a ser respeitado.

Para criar um banco novo:

```bash
python init_db.py
```

Por seguranca, `init_db.py` nao cria mais usuario admin padrao. Para criar um seed inicial, defina explicitamente:

```bash
SEED_ADMIN_EMAIL=admin@seudominio.com
SEED_ADMIN_PASSWORD=uma-senha-forte-com-12-ou-mais-caracteres
SEED_COMPANY_NAME=AutoFlow
python init_db.py
```

Nunca use senha fraca em seed de producao.

Para maior volume, a evolucao recomendada e migrar para PostgreSQL mantendo os filtros por `empresa_id`, indices e validacoes de ownership.

## Desenvolvimento Local

```bash
pip install -r requirements.txt
python init_db.py
python app.py
```

`python app.py` deve ser usado apenas para desenvolvimento/local.

## Variaveis De Ambiente

- `SECRET_KEY`: chave secreta do Flask
- `OPENAI_API_KEY`: chave da OpenAI
- `OPENAI_MODEL`: modelo usado pela IA
- `DATABASE_PATH`: caminho do banco SQLite
- `REDIS_URL`: URL do Redis
- `RATELIMIT_STORAGE_URI`: storage compartilhado do rate limit
- `CACHE_REDIS_URL`: Redis usado pelo cache
- `LOG_LEVEL`: nivel de logs
- `TRUST_PROXY_HEADERS`: use `True` somente atras de proxy confiavel
- `HOST`: host local usado por `python app.py`
- `PORT`: porta local usada por `python app.py`
- `SESSION_COOKIE_SECURE`: use `True` com HTTPS
- `SESSION_COOKIE_SAMESITE`: politica SameSite do cookie
- `META_APP_SECRET`: segredo do app Meta para validar `X-Hub-Signature-256`
- `META_GRAPH_BASE_URL`: URL base da Graph API
- `META_GRAPH_VERSION`: versao da Graph API
- `MERCADO_PAGO_WEBHOOK_SECRET`: segredo do webhook Mercado Pago
- `MERCADO_PAGO_API_KEY`: token para confirmar pagamentos na API Mercado Pago
- `MERCADO_PAGO_API_BASE_URL`: URL base da API Mercado Pago
- `SEED_ADMIN_EMAIL`: e-mail opcional para seed inicial
- `SEED_ADMIN_PASSWORD`: senha forte opcional para seed inicial
- `SEED_COMPANY_NAME`: empresa opcional para seed inicial

## Webhooks

WhatsApp:

```text
/webhooks/whatsapp/<token>
```

Instagram:

```text
/webhooks/instagram/<token>
```

Quando `META_APP_SECRET` estiver configurado, os webhooks Meta devem enviar assinatura valida em `X-Hub-Signature-256`.

Mercado Pago:

```text
/webhooks/mercadopago
```

O webhook Mercado Pago exige segredo configurado e assinatura valida.

## Testes

```bash
python -m pytest
```

## Estrutura

- `app.py`: aplicacao principal e compatibilidade das rotas antigas
- `routes/`: blueprints ativos
- `services/`: servicos extraidos do fluxo principal
- `utils/`: banco, auth, cache, limiter e normalizadores
- `database/schema.sql`: schema base para banco novo
- `tests/`: testes automatizados
- `wsgi.py`: entrada WSGI para Gunicorn

## Estado Atual

Projeto funcional em evolucao para producao. SQLite ainda e suportado, mas exige cuidado operacional com backup, volume e concorrencia.
