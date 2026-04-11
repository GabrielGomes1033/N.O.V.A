# Comandos da NOVA

Este arquivo reúne os comandos disponíveis no projeto e mostra exemplos prontos para usar no chat.

## Trocar o modo da assistente

Use este comando para mudar o estilo de resposta da NOVA.

Formato:
```text
/modo <nome_do_modo>
```

Exemplos:
```text
/modo normal
/modo formal
/modo engracado
/modo sarcastico
/modo inspirador
/modo tecnologico
```

## Ensinar uma nova resposta

Use este comando para ensinar uma pergunta e a resposta que a NOVA deve guardar.

Formato:
```text
/ensinar pergunta = resposta
```

Exemplo:
```text
/ensinar quem é o homem de ferro = Tony Stark
```

## Aprender

Este comando funciona da mesma forma que `/ensinar`.

Formato:
```text
/aprender pergunta = resposta
```

Exemplo:
```text
/aprender quem criou o python = Guido van Rossum
```

## Ver memória

Mostra os dados que a NOVA está lembrando sobre você.

Formato:
```text
/memoria
```

## Definir seu nome

Salva seu nome no perfil da conversa.

Formatos:
```text
/meu_nome Nome
/nome Nome
```

Exemplo:
```text
/meu_nome Gabriel
```

## Definir idioma preferido

Troca o idioma preferido salvo no perfil.

Formato:
```text
/idioma pt
/idioma en
/idioma es
```

## Definir tratamento

Salva um jeito preferido de ser chamado.

Formato:
```text
/me_chame apelido
/tratamento apelido
```

Exemplo:
```text
/me_chame chefe
```

## Esquecer dados do perfil

Apaga partes da memória da NOVA.

Formatos:
```text
/esquecer nome
/esquecer idioma
/esquecer tratamento
/esquecer memoria
```

## Pesquisar e resumir

Use estes comandos para pedir uma pesquisa. A NOVA tenta buscar um resumo na Wikipedia, mostra o link e lê o resumo em voz.

Formatos:
```text
/google assunto
/pesquisar assunto
```

Exemplos:
```text
/google inteligência artificial
/pesquisar Brasil
/pesquisar clima em São Paulo
```

## Modo agente (planejar e agir)

Use este comando para a NOVA atuar como agente: ela cria um plano, executa passos e retorna observações.

Formato:
```text
/nova <objetivo>
```

Exemplos:
```text
/nova organize meu dia: estudo urgente, mercado, treino
/nova pesquise sobre computação quântica
/nova mercado hoje
/nova relembre meus objetivos
/nova abra no google python agent
```

Observações:
- Ações sensíveis (como abrir navegador) pedem confirmação.
- Responda `sim` para executar ou `não` para cancelar.
- Objetivos recentes ficam salvos na memória de longo prazo.
- O modo agente agora executa plano por etapas com status (`pendente`, `executando`, `concluido`, `falhou`).
- O aprendizado padrão via `/ensinar` foi mantido sem alterações.
- Compatibilidade: `/agente` ainda funciona, mas o comando oficial agora é `/nova`.

## Comandos de admin

Use esses comandos para operações administrativas e explicação técnica completa da arquitetura.

Formatos:
```text
/admin login <usuario> <senha>
/admin logout
/admin status
/admin explicar
/admin configurar <novo_usuario> <nova_senha>
```

Exemplos:
```text
/admin login admin admin123
/admin status
/admin explicar
/admin configurar root senha_forte_2026
```

Observações:
- `/admin explicar` é restrito a sessão autenticada.
- Se a senha padrão estiver ativa, troque com `/admin configurar`.
- Dados persistidos agora usam criptografia em repouso via camada de segurança.

## Despertador inteligente (admin)

Somente admin autenticado pode controlar esta função.

Formatos:
```text
/admin despertador status
/admin despertador ligar HH:MM [cidade] [nome]
/admin despertador desligar
/admin despertador testar
```

Exemplos:
```text
/admin login mestre senha_super_2026
/admin despertador ligar 07:00 Sao_Paulo Gabriel
/admin despertador status
/admin despertador testar
/admin despertador desligar
```

Comportamento:
- No horário definido, a NOVA diz bom dia com data e clima da cidade.
- Em seguida, informa resumo do mercado tradicional (índices) e do mercado cripto.
- O teste manual dispara a mensagem na hora, sem esperar o horário.

## JARVIS fase 2 (admin)

Execução contínua em background com fila de tarefas e relatórios proativos automáticos.

Formatos:
```text
/admin jarvis2 status
/admin jarvis2 ligar [intervalo_min]
/admin jarvis2 desligar
/admin jarvis2 enfileirar <objetivo>
/admin jarvis2 fila
/admin jarvis2 limpar
/admin jarvis2 relatorio
```

Exemplo:
```text
/admin login mestre senha_super_2026
/admin jarvis2 ligar 15
/admin jarvis2 enfileirar organizar meu dia: estudo, treino, mercado
/admin jarvis2 fila
/admin jarvis2 relatorio
```

## Backup secundário no Google Drive (admin)

Use para manter cópia secundária da memória da NOVA na nuvem do Drive.

Formatos:
```text
/admin drivebackup status
/admin drivebackup sincronizar
/admin drivebackup restaurar
```

## Ativar a voz

Liga o retorno de voz da NOVA.

Formato:
```text
/voz on
```

Exemplos:
```text
/voz on
/voz ligar
/voz ativar
```

## Desativar a voz

Desliga o retorno de voz da NOVA.

Formato:
```text
/voz off
```

Exemplos:
```text
/voz off
/voz desligar
/voz desativar
```

## Observações

- Você também pode conversar com a NOVA sem usar comandos, como se estivesse falando com uma pessoa.
- Quando a voz estiver ativa, ela pode ler respostas normais e também os resumos das pesquisas.
- Os comandos de pesquisa atualmente usam a Wikipedia como fonte principal de resumo e o Google como alternativa.
