# Guia Completo do Backend Python (NOVA)

Este guia explica o backend da NOVA de forma didatica, como um dev explicaria para outro dev que esta comecando.

## 1) Visao geral rapida

O backend atual e um app Python de terminal.
Ele faz 5 coisas principais:
1. Conversa com o usuario (chat em loop).
2. Detecta intencao da frase.
3. Busca resposta em base pronta + aprendizado salvo.
4. Opcionalmente fala a resposta em voz (TTS).
5. Oferece recursos de admin para seguranca e explicacao interna.

## 2) Estrutura de pastas do backend

```text
backend_python/
├── main.py
├── requirements.txt
├── data/
│   ├── aprendizado.json
│   └── memoria_usuario.json
├── core/
│   ├── respostas.py
│   ├── memoria.py
│   ├── seguranca.py
│   ├── admin.py
│   ├── despertador.py
│   ├── jarvis_fase2.py
│   ├── backup_drive.py
│   ├── caminhos.py
│   ├── pesquisa.py
│   ├── voz.py
│   ├── voz_worker.py
│   ├── personalidade.py
│   ├── logica.py
│   ├── modos.txt
│   └── aprendizado.json (legado)
└── app/
    └── gerar_modos.py
```

## 3) Fluxo principal de execucao

1. O Python inicia em `main.py`.
2. `main.py` tenta importar o nucleo (`core.*`).
3. Se o core falhar, ele usa funcoes fallback para nao quebrar.
4. Entra no loop de terminal (`while True`).
5. Para cada entrada:
   - trata comandos (`/ensinar`, `/google`, `/nome`);
   - se for conversa normal, chama `detectar_intencao` e `responder`;
   - imprime resposta;
   - tenta falar com TTS (`falar`).

Arquivo: [main.py](/home/dev-0/Documentos/ChatBot/backend_python/main.py)

## 4) `main.py` explicado ponto a ponto

### Bloco de seguranca (erro + fallback)

- `registrar_erro(exc)`: salva stack trace em `erro_log.txt`.
- Fallbacks (`responder`, `detectar_intencao`, etc.): garantem que o app continue mesmo se o core falhar no import.
- `try/except` de import: tenta carregar funcoes reais do `core`. Se der erro, registra log e segue com fallback.

### Contexto em memoria de execucao

`contexto` e um dicionario simples com:
- `nome_usuario`
- `idioma_preferido`

Esse contexto vai sendo passado para o motor de resposta.

### Comandos de terminal

- `comando_ensinar`: salva pergunta/resposta no aprendizado.
- `comando_google`: tenta resumo da Wikipedia; se nao achar, abre busca Google.
- `comando_nome`: define nome no contexto atual.

### Loop principal

No `main()`:
1. Mostra saudacao.
2. Le entrada com `input`.
3. Ignora vazio.
4. Sai com `sair`.
5. Roteia comandos.
6. Se nao for comando: conversa normal.

## 5) Motor de linguagem (`core/respostas.py`)

Arquivo: [respostas.py](/home/dev-0/Documentos/ChatBot/backend_python/core/respostas.py)

Esse e o coracao da NOVA. Ele concentra:
1. Deteccao de intencao.
2. Carga de respostas por modo.
3. Carga e salvamento de aprendizado do usuario.
4. Respostas contextuais (mais humanas).
5. Fallback quando nao entende.
6. Estilizacao final.

### Componentes importantes

- `INTENCOES`: mapa grande de intencao -> frases gatilho (pt/en/es).
- `normalizar_texto`: remove acento, pontuacao e padroniza.
- `detectar_intencao`: tenta match por palavra-chave, contexto e similaridade.
- `carregar_respostas`: le `modos.txt` e separa respostas por modo.
- `carregar_aprendizado` / `salvar_aprendizado`: persistencia de respostas ensinadas.
- `buscar_resposta_aprendida`: prioridade para conhecimento customizado.
- `responder_com_contexto`: gera frases mais naturais baseadas no momento da conversa.
- `responder`: funcao final que decide a resposta e aplica placeholders (`{hora}`, `{data}`, `{usuario}`).

### Ordem de decisao da resposta (muito importante)

Dentro de `responder(...)`, a prioridade e:
1. Resposta aprendida pelo usuario.
2. Resposta contextual (se houver regra).
3. Resposta por intencao no `modos.txt`.
4. Resposta de desconhecido mais humana.

Isso deixa o bot mais adaptavel sem perder fallback.

## 6) Memoria persistente (`core/memoria.py`)

Arquivo: [memoria.py](/home/dev-0/Documentos/ChatBot/backend_python/core/memoria.py)

Guarda perfil simples do usuario com persistencia protegida:
- nome
- idioma preferido
- tratamento
- topicos favoritos

Funcoes principais:
1. `carregar_memoria_usuario`: le JSON com validacao.
2. `salvar_memoria_usuario`: grava JSON de forma segura.
3. `atualizar_memoria_usuario`: atualiza campos especificos.
4. `esquecer_memoria`: limpa um campo ou tudo.
5. `formatar_memoria_usuario`: monta resumo pronto para chat.

## 6.1) Seguranca (`core/seguranca.py`)

Arquivo: [seguranca.py](/home/dev-0/Documentos/ChatBot/backend_python/core/seguranca.py)

Centraliza:
1. Criptografia de dados em repouso com Fernet (quando disponivel).
2. Leitura/escrita segura de JSON (`carregar_json_seguro`/`salvar_json_seguro`).
3. Hash de senha admin com PBKDF2-HMAC-SHA256.

## 6.2) Admin (`core/admin.py`)

Arquivo: [admin.py](/home/dev-0/Documentos/ChatBot/backend_python/core/admin.py)

Responsavel por:
1. Login admin.
2. Rotacao de credenciais.
3. Status de seguranca.
4. Explicacao completa da arquitetura via comando restrito.

## 6.3) Despertador inteligente (`core/despertador.py`)

Arquivo: [despertador.py](/home/dev-0/Documentos/ChatBot/backend_python/core/despertador.py)

Responsavel por:
1. Agendar disparo diário em horário configurado.
2. Montar mensagem "Bom dia Senhor <nome>" com data e clima.
3. Buscar resumo de mercado tradicional e cripto.
4. Permitir teste manual e controle via comandos admin.

## 6.4) JARVIS fase 2 (`core/jarvis_fase2.py`)

Arquivo: [jarvis_fase2.py](/home/dev-0/Documentos/ChatBot/backend_python/core/jarvis_fase2.py)

Responsavel por:
1. Runtime contínuo em background.
2. Fila persistente de tarefas.
3. Execução automática de objetivos.
4. Relatórios proativos em intervalo configurável.

## 6.5) Backup Google Drive (`core/backup_drive.py`)

Arquivo: [backup_drive.py](/home/dev-0/Documentos/ChatBot/backend_python/core/backup_drive.py)

Responsavel por:
1. Status do backup secundário.
2. Sincronização da memória para arquivo remoto no Drive.
3. Restauração da memória a partir do backup remoto.

## 7) Caminhos de dados (`core/caminhos.py`)

Arquivo: [caminhos.py](/home/dev-0/Documentos/ChatBot/backend_python/core/caminhos.py)

`pasta_dados_app()`:
1. Descobre raiz do backend.
2. Garante pasta `data/`.
3. Retorna caminho para outros modulos gravarem arquivos.

Resumo: esse modulo evita hardcode de caminho espalhado no projeto.

## 8) Pesquisa externa (`core/pesquisa.py`)

Arquivo: [pesquisa.py](/home/dev-0/Documentos/ChatBot/backend_python/core/pesquisa.py)

Responsabilidade: buscar resumo curto na Wikipedia.

Fluxo:
1. Sanitiza consulta.
2. Tenta achar titulo com API `opensearch`.
3. Busca resumo com API `page/summary`.
4. Encurta para leitura natural.
5. Tenta PT primeiro, depois EN.

Saida: dict com `titulo`, `resumo`, `fonte`, `url`.

## 9) Personalidade e estilo (`core/personalidade.py`)

Arquivo: [personalidade.py](/home/dev-0/Documentos/ChatBot/backend_python/core/personalidade.py)

Controla "tom de voz" por modo:
- normal
- engracado
- formal
- sarcastico
- inspirador
- tecnologico

Como funciona:
1. `set_modo(modo)` troca modo global.
2. `estilizar(resposta)` sorteia prefixo/sufixo do modo e aplica na resposta.

## 10) Voz (TTS) (`core/voz.py` + `core/voz_worker.py`)

Arquivos:
- [voz.py](/home/dev-0/Documentos/ChatBot/backend_python/core/voz.py)
- [voz_worker.py](/home/dev-0/Documentos/ChatBot/backend_python/core/voz_worker.py)

### Por que tem 2 arquivos?

- `voz.py`: orquestra e decide se pode falar.
- `voz_worker.py`: gera e toca audio em processo separado.

### Fluxo de voz

1. `falar(texto)` valida disponibilidade (`edge_tts`, player, worker).
2. Limpa e humaniza texto (`preparar_texto_para_voz`).
3. Encerra processo de voz anterior (evita sobreposicao).
4. Abre subprocesso chamando `voz_worker.py`.
5. Worker gera mp3 com `edge_tts`.
6. Worker toca audio com `gst-play-1.0`.

### Beneficio tecnico

Processo separado reduz travamento da thread principal do chat.

## 11) Compatibilidade (`core/logica.py`)

Arquivo: [logica.py](/home/dev-0/Documentos/ChatBot/backend_python/core/logica.py)

Esse modulo so reexporta `responder` para imports antigos nao quebrarem.

## 12) Gerador de base de respostas (`app/gerar_modos.py`)

Arquivo: [gerar_modos.py](/home/dev-0/Documentos/ChatBot/backend_python/app/gerar_modos.py)

Script utilitario para montar `core/modos.txt` em massa.

Ele:
1. Define modos.
2. Define intencoes com frases base.
3. Faz combinacoes aleatorias com emojis/variacoes.
4. Gera milhares de frases por intencao.

Observacao: e um gerador de dataset textual, nao roda no fluxo principal do chat.

## 13) Dependencias (`requirements.txt`)

Arquivo: [requirements.txt](/home/dev-0/Documentos/ChatBot/backend_python/requirements.txt)

Principais usadas hoje:
- `requests`: pesquisa Wikipedia.
- `edge-tts`: sintese de voz neural.
- `pyttsx3`: alternativa de TTS local (nao e a principal no fluxo atual).

Dependencias como `Cython`, `docutils`, `Pillow`, `Pygments` podem ser legado ou suporte indireto.

## 14) Como rodar backend local

```bash
cd /home/dev-0/Documentos/N.O.V.A/backend_python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 14.1) Rodar API para o app mobile

Para conectar o Flutter no celular com o backend real:

```bash
cd /home/dev-0/Documentos/N.O.V.A
scripts/start_api.sh
```

Endpoints:
- `GET /health`
- `POST /chat` com body JSON `{"message":"..."}`.

Se quiser trocar a porta local sem editar codigo:

```bash
export NOVA_API_PORT=8119
scripts/start_api.sh
```

Rotas protegidas por token:
- Defina `NOVA_API_TOKEN` ou `NOVA_API_TOKENS` no backend para conseguir autenticar chamadas protegidas.
- Os headers aceitos sao `Authorization: Bearer <token>` e `X-API-Key: <token>`.
- Exemplos de rotas protegidas: `GET /ops/status`, `GET /system/status` e `POST /documents/analyze`.

## 15) Linha por linha: pontos mais criticos para aprender

Se voce quiser focar no que mais importa primeiro, estude nesta ordem:
1. `main.py`: entender roteamento de comandos vs conversa.
2. `respostas.py`: entender pipeline de decisao.
3. `memoria.py`: entender persistencia simples em JSON.
4. `voz.py` + `voz_worker.py`: entender subprocesso para I/O pesado.
5. `pesquisa.py`: entender integracao HTTP externa.

## 16) Checklist mental de arquitetura (resumo final)

1. Entrada: `main.py`
2. Regras de linguagem: `core/respostas.py`
3. Memoria do usuario: `core/memoria.py` + `data/*.json`
4. Pesquisa externa: `core/pesquisa.py`
5. Voz: `core/voz.py` + `core/voz_worker.py`
6. Estilo/persona: `core/personalidade.py`

Se quiser, no proximo passo eu faco uma versao 2 deste guia com "linha por linha literal" do `main.py` e do `respostas.py`, numerando cada bloco e explicando impacto de alterar cada linha.
