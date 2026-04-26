# Guia do Frontend Flutter (NOVA)

Este documento explica o codigo Flutter do projeto e a funcao de cada parte, em linguagem simples.

## 1) Objetivo do frontend

O frontend em Flutter e a camada visual da NOVA.  
Ele mostra telas, recebe interacoes do usuario (toque, digitacao) e, no futuro, vai conversar com o backend Python via API.

## 2) Estrutura atual

```text
frontend_flutter/
├── lib/
│   ├── main.dart
│   ├── app.dart
│   ├── screens/
│   │   └── home_page.dart
│   ├── widgets/
│   │   └── feature_card.dart
│   └── theme/
│       └── app_theme.dart
├── pubspec.yaml
└── analysis_options.yaml
```

## 3) Explicacao arquivo por arquivo

### `lib/main.dart`

- Funcao: ponto de entrada do app.
- O que acontece:
1. O Flutter executa `main()`.
2. `runApp(...)` sobe o primeiro widget da arvore.
3. Esse widget raiz e `NovaFrontendApp`.

### `lib/app.dart`

- Funcao: configurar o aplicativo globalmente.
- Responsabilidades:
1. Criar `MaterialApp` (estrutura base do app Flutter).
2. Definir titulo do app.
3. Definir tema global (`AppTheme.lightTheme`).
4. Definir a tela inicial (`HomePage`).

### `lib/theme/app_theme.dart`

- Funcao: concentrar cores e estilo visual do app.
- Beneficio: voce muda o visual inteiro num ponto unico.
- Hoje ele define:
1. Cores principais.
2. Tema claro (`ThemeData`).
3. Estilo do `AppBar`.
4. Estilo de `Card`.

### `lib/screens/home_page.dart`

- Funcao: primeira tela do usuario.
- Conceitos Flutter mostrados:
1. `StatefulWidget`: tela que muda com o tempo.
2. `setState(...)`: avisa o Flutter para redesenhar a interface.
3. `TextEditingController`: controla texto do campo de entrada.
4. `dispose()`: libera recursos quando a tela e destruida.

- Fluxo da tela:
1. Usuario digita mensagem no `TextField`.
2. Usuario toca em `Enviar`.
3. `_handleSendMessage()` valida a mensagem.
4. `setState` atualiza `_lastMessage`.
5. A interface reflete o novo valor na hora.

### `lib/widgets/feature_card.dart`

- Funcao: componente reutilizavel de card informativo.
- Vantagem: evita repeticao de codigo e facilita manutencao.
- Parametros:
1. `title`: titulo do card.
2. `description`: texto explicativo.

### `pubspec.yaml`

- Funcao: manifesto do projeto Flutter.
- Contem:
1. Nome e versao do app.
2. Faixa de versao do Dart.
3. Dependencias de execucao e desenvolvimento.
4. Configuracoes do Flutter (ex.: icones material).

### `analysis_options.yaml`

- Funcao: regras de qualidade/lint.
- Ajuda a padronizar o codigo e evitar erros comuns.

## 4) Como o app funciona por dentro

Em Flutter, tudo e widget.  
Sua tela e uma arvore de widgets aninhados:

1. `MaterialApp`
2. `Scaffold`
3. `AppBar` e `body`
4. Dentro do `body`, widgets como `Text`, `TextField`, `FilledButton`, etc.

Quando o estado muda (`setState`), o Flutter reconstrói os widgets necessarios.

## 5) Como executar (quando o Flutter estiver instalado)

No terminal:

```bash
cd /home/dev-0/Documentos/N.O.V.A/frontend_flutter
flutter pub get
flutter run --dart-define=NOVA_API_URL=http://SEU_IP_LOCAL:8000
```

Exemplo real:

```bash
flutter run --dart-define=NOVA_API_URL=http://192.168.0.25:8000
```

Importante:
- `SEU_IP_LOCAL` deve ser o IP do computador onde a API Python está rodando.
- Celular e computador precisam estar na mesma rede.
- Se a API local estiver em outra porta, voce pode informar so a porta do auto-detect com `--dart-define=NOVA_API_PORT=8119` ou passar a URL completa com a porta correta.

## 6) Gerar base nativa completa (android/ios/web)

No momento, o ambiente atual nao tem Flutter CLI instalado (`flutter: command not found`).  
Assim que instalar Flutter localmente, rode:

```bash
cd /home/dev-0/Documentos/N.O.V.A/frontend_flutter
flutter create .
```

Esse comando cria/atualiza os arquivos nativos completos em:
- `android/`
- `ios/`
- `web/`
- `linux/`, `macos/`, `windows/` (dependendo da plataforma)

## 7) Proximos passos recomendados

1. Criar uma camada `services/` para chamadas HTTP.
2. Conectar o frontend ao backend Python (endpoint de chat).
3. Trocar o estado local por `ValueNotifier`, `Provider` ou `Riverpod` quando o app crescer.
4. Adicionar testes de widget em `test/`.

## 8) Microfone e execucao de comandos

O frontend agora possui reconhecimento de fala.

### O que foi adicionado

1. Dependencia `speech_to_text` no `pubspec.yaml`.
2. Permissao Android `RECORD_AUDIO` no `AndroidManifest.xml`.
3. Permissoes iOS `NSMicrophoneUsageDescription` e `NSSpeechRecognitionUsageDescription` no `Info.plist`.
4. Botao de microfone na tela inicial para iniciar/parar escuta.
5. Execucao automatica quando a fala final e reconhecida.

### Fluxo da funcao de voz

1. Usuario toca em `Ouvir`.
2. App inicia escuta em `pt_BR`.
3. Texto reconhecido aparece no campo em tempo real.
4. Quando o resultado final chega, o comando e executado automaticamente.
5. O painel mostra status no bloco `Diagnostico`.

### Comandos locais disponiveis

1. `/ouvir`: inicia escuta de voz.
2. `/parar`: encerra escuta.
3. `/status`: mostra estado do sistema e microfone.
4. `/limpar`: limpa estado exibido na tela.
