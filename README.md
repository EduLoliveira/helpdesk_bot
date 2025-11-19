🤖 PROJETO_AI - Sistema de Automação para Help Desk
Sistema inteligente que simula um bot para automação de processos de suporte técnico, incluindo monitoramento de chamados, notificações automáticas e geração de insights atraves dos dados.

🗂️ Estrutura do Projeto
text
PROJETO_AI/
├── 📁 app_project/                 # Aplicação principal
│   ├── 📁 migrations/             # Migrações do banco de dados
│   ├── 📁 templates/              # Templates HTML
│   ├── 📄 apps.py                 # Configuração do app
│   ├── 📄 bot_dialogos.py         # Lógica do bot e diálogos
│   ├── 📄 forms.py                # Formulários Django
│   ├── 📄 models.py               # Modelos de dados
│   ├── 📄 security.py             # Configurações de segurança
│   ├── 📄 tests.py                # Testes da aplicação
│   ├── 📄 urls.py                 # URLs do app
│   └── 📄 views.py                # Views da aplicação
├── 📁 api/                        # API para integrações
├── 📁 chatAI_project/             # Configurações do projeto Django
│   ├── 📄 __init__.py
│   ├── 📄 settings.py             # Configurações do projeto
│   ├── 📄 urls.py                 # URLs principais
│   ├── 📄 asgi.py                 # Configuração ASGI
│   └── 📄 wsgj.py                 # Configuração WSGI
├── 📁 static/                     # Arquivos estáticos
│   ├── 📁 css/                    # Folhas de estilo
│   │   ├── 📄 chamados.css
│   │   ├── 📄 home.css
│   │   ├── 📄 homeNotificacoes.css
│   │   └── 📄 initial.css
│   └── 📁 js/                     # Scripts JavaScript
├── 📁 venv/                       # Ambiente virtual Python
├── 📄 db.sqlite3                  # Banco de dados SQLite
├── 📄 manage.py                   # Script de gerenciamento Django
└── 📄 README.md                   # Documentação do projeto

## 🚀 Funcionalidades Principais

### 🤖 Automações do Bot
- **Monitoramento de Chamados** - Acompanhamento em tempo real
- **Notificações Automáticas** - Alertas inteligentes
- **Geração de Relatórios** - Análise de dados e métricas
- **Integração com ChatBot** - API para sistemas de mensagens
- **Abertura de Chamados** - Criação e confirmação automatizada

## 👥 API de Usuários

Sistema completo de gerenciamento de usuários incluindo:
- Cadastro e autenticação de usuários
- Perfis de acesso diferenciados
- Gestão de permissões
- Integração com sistema de notificações

## 🛠️ Configuração do Ambiente

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual (Windows)
venv\Scripts\activate

# Instalar dependências
pip install -r requirements.txt

# Executar migrações
python manage.py migrate

# Iniciar servidor
python manage.py runserver
⚡ Sistema desenvolvido para otimizar processos de suporte técnico através de automação inteligente!