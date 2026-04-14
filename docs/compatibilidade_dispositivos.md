# Compatibilidade da NOVA

## Resumo
- Android (celular/tablet): suporte completo.
- iOS (iPhone/iPad): suporte parcial, sem wake word em background nesta versão.
- Desktop (Windows/Linux/macOS): suporte de UI e chat, wake word em background não disponível.

## Matriz por recurso
- Wake word em primeiro plano: Android, iOS, Desktop.
- Wake word em segundo plano: Android.
- Biblioteca de músicas local: Android, iOS, Desktop.
- Notificações de lembrete: Android, iOS.
- Pesquisa web/mercado/Drive (via backend): Android, iOS, Desktop.

## Observações
- Recursos web dependem de backend ativo e internet.
- O serviço de background no Android usa `Foreground Service` + `SpeechRecognizer`.
