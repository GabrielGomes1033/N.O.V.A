# Integração da NOVA com Notion

Este guia habilita a criação de projetos no Notion por voz ou texto.

## 1) Criar a integração no Notion

Crie uma integração interna no Notion e copie o token.

Permissões recomendadas:
- `Insert content`
- `Read content` para a NOVA descobrir automaticamente a coluna de título do banco

## 2) Compartilhar o destino com a integração

Você pode usar um destes destinos:
- Um `data source` de projetos, para cada projeto virar um item do banco
- Uma `page`, para cada projeto virar uma subpágina

Compartilhe esse destino com a integração criada no passo anterior.

## 3) Configurar o `.env.nova`

Exemplo:

```text
NOVA_NOTION_TOKEN=secret_xxxxx
NOVA_NOTION_PROJECTS_DATA_SOURCE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOVA_PROJECT_PROVIDER=notion
```

Se você só tiver o ID do database, também pode usar:

```text
NOVA_NOTION_TOKEN=secret_xxxxx
NOVA_NOTION_PROJECTS_DATABASE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOVA_PROJECT_PROVIDER=notion
```

Alternativa com página:

```text
NOVA_NOTION_TOKEN=secret_xxxxx
NOVA_NOTION_PROJECTS_PAGE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
NOVA_PROJECT_PROVIDER=notion
```

Se a coluna de título do banco não for detectada automaticamente, defina também:

```text
NOVA_NOTION_PROJECTS_TITLE_PROPERTY=Nome
```

Se você quiser preencher automaticamente mais colunas, pode configurar também:

```text
NOVA_NOTION_PROJECTS_DESCRIPTION_PROPERTY=Descrição
NOVA_NOTION_PROJECTS_AREA_PROPERTY=Área
NOVA_NOTION_PROJECTS_PRIORITY_PROPERTY=Prioridade
NOVA_NOTION_PROJECTS_RESPONSIBLE_PROPERTY=Responsável
NOVA_NOTION_PROJECTS_LINK_PROPERTY=Link
NOVA_NOTION_PROJECTS_STATUS_PROPERTY=Status
NOVA_NOTION_PROJECTS_STATUS_VALUE=Backlog
```

## 4) Subir a API

```bash
scripts/start_api.sh
```

## 5) Testar no chat

Use qualquer uma destas frases:

```text
Nova, crie um novo projeto chamado Atlas Comercial
Nova, abre um projeto novo CRM Interno
Novo projeto "Planejamento Q4"
Nova, crie um projeto chamado Atlas Comercial na área Comercial com prioridade Alta
Nova, cria um projeto chamado Portal do Cliente com descrição MVP do portal B2B e link https://exemplo.com
Nova, cria um projeto chamado CRM Interno com responsável Gabriel Gomes
/projeto Assistente Financeiro IA
/notion projeto Roadmap 2026
```

## Comportamento

- Voz e texto convergem para o mesmo backend.
- Se a frase mencionar `Notion`, a NOVA prioriza o Notion.
- Se a frase mencionar `Drive`, a NOVA força o Google Drive.
- Se nenhum provider for citado, a NOVA usa `NOVA_PROJECT_PROVIDER`.
