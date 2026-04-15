# HilFlow Automação

Plataforma completa de CRM + Central de Atendimento Inteligente com automação via bot IA e WhatsApp.

## Funcionalidades Implementadas

- ✅ **Multiempresa Real**: Isolamento completo por empresa
- ✅ **Fluxos Operacionais**: Editor visual, execução bloco a bloco
- ✅ **Atendimento Humano**: Assumir, pausar bot, fila profissional
- ✅ **Tags Funcionais**: Criar, aplicar, filtrar em automação
- ✅ **Logs/Eventos**: Rastreamento detalhado de ações
- ✅ **Agendamento Inteligente**: Validação de conflitos e disponibilidade
- ✅ **Regras Avançadas**: Prioridade, múltiplas ações, condições complexas
- ✅ **Integração WhatsApp**: Via Twilio para mensagens reais

## Setup

1. Clone o repositório.
2. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```
3. Configure o ambiente:
   - Copie `.env.example` para `.env` e preencha as variáveis.
4. Inicialize o banco de dados:
   ```
   python init_db.py
   ```
5. Execute o app:
   ```
   python app.py
   ```
   Ou com Docker:
   ```
   docker-compose up
   ```

## Variáveis de Ambiente

- `SECRET_KEY`: Chave secreta para sessões Flask.
- `OPENAI_API_KEY`: Chave da API OpenAI.
- `OPENAI_MODEL`: Modelo GPT (padrão: gpt-4o-mini).
- `DATABASE_PATH`: Caminho do banco SQLite (padrão: database/hilflow.db).
- `REDIS_URL`: URL Redis para cache.
- `TWILIO_ACCOUNT_SID`: SID da conta Twilio.
- `TWILIO_AUTH_TOKEN`: Token Twilio.
- `TWILIO_PHONE_NUMBER`: Número WhatsApp Twilio.
- `DEBUG`: Modo debug (True/False).

## WhatsApp Integration

1. Configure conta Twilio e WhatsApp Sandbox.
2. Defina webhook: `https://seudominio.com/api/webhook/whatsapp`
3. Teste enviando mensagens do WhatsApp.

## Estrutura

- `app.py`: Aplicação principal com blueprints.
- `routes/`: Módulos de rotas (auth, dashboard, regras, api, fluxos, fluxo_editor).
- `services/`: Lógica de negócio (regras_service).
- `templates/`: Templates HTML responsivos.
- `static/`: CSS e arquivos estáticos.
- `database/`: Schema SQL completo.
- `utils/`: Utilitários (auth, db, whatsapp, cache).

## Desenvolvimento

- Use virtualenv para isolamento.
- Testes: `pytest`
- Code style: Mantenha consistência com código existente.
- Execute testes (a implementar).
- Contribua via pull requests.