# unispam

Ferramenta para envio de mensagens em massa via Moodle (campus.isutc.ac.mz).

## Estrutura

```
unispam/
├── client.py       # MoodleClient — login, send, search
├── enumerate.py    # Recolhe todos os utilizadores → SQLite
├── send.py         # Envia mensagens (single / batch)
├── users.db        # Base de dados gerada pelo enumerate
└── .env            # Credenciais (não commitar)
```

## Setup

```bash
pip install requests python-dotenv
cp .env.example .env
# editar .env com credenciais reais
```

**.env**
```
MOODLE_USER=nome.apelido
MOODLE_PASS=password
```

---

## enumerate.py — Recolher utilizadores

Percorre o alfabeto (a–z + acentuados) via API de pesquisa de mensagens, pagina os resultados e guarda em SQLite.

```bash
python enumerate.py                      # guarda em users.db
python enumerate.py --db users.db --delay 0.5
```

| Opção | Descrição | Default |
|-------|-----------|---------|
| `--db` | Ficheiro SQLite de output | `users.db` |
| `--delay` | Segundos entre requests | `0.3` |

**Schema da DB:**
```sql
users (id INTEGER PRIMARY KEY, fullname TEXT, profileurl TEXT)
```

---

## send.py — Enviar mensagens

### Single — um utilizador por ID

```bash
python send.py single 422 --message "Olá!"
python send.py single 422                     # pede mensagem interactivamente
python send.py single 422 --message "Olá!" --dry-run
```

### Batch — múltiplos utilizadores

```bash
# Todos os utilizadores da DB
python send.py batch --message "Olá {name}!"

# IDs específicos
python send.py batch --ids 422,163,538 --message "Olá {name}!"

# Primeiros N utilizadores
python send.py batch --limit 100 --message "Olá {name}!"

# Mensagem de ficheiro
python send.py batch --message-file msg.txt --delay 2

# Preview sem enviar
python send.py batch --message "Olá {name}!" --dry-run
```

| Opção | Descrição | Default |
|-------|-----------|---------|
| `--ids` | IDs separados por vírgula | todos na DB |
| `--limit` | Máximo de destinatários | sem limite |
| `--message` / `-m` | Texto da mensagem | — |
| `--message-file` | Ler mensagem de ficheiro | — |
| `--delay` | Segundos entre envios | `1.0` |
| `--dry-run` | Simula sem enviar | `false` |

**Placeholders na mensagem:**
- `{name}` → primeiro nome
- `{fullname}` → nome completo

