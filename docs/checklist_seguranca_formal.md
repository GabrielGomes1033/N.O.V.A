# Checklist Formal de Segurança (NOVA)

## Escopo
- Tokens e segredos
- Permissões e superfície de ataque
- Acesso administrativo
- Hardening e resposta a incidentes

## 1. Tokens e Segredos
- [ ] Tokens nunca em texto puro no banco local
- [ ] Rotação periódica de credenciais externas (Telegram/API)
- [ ] Revogação imediata após suspeita de vazamento
- [ ] Segredos com escopo mínimo e sem reutilização entre ambientes

## 2. Permissões e Superfície de Ataque
- [ ] Permissões de app reduzidas ao mínimo necessário
- [ ] Serviços em background com finalidade explícita
- [ ] Endpoints administrativos protegidos e monitorados
- [ ] Ações sensíveis exigem autenticação forte

## 3. Acesso Administrativo
- [ ] Senha padrão de admin desativada
- [ ] Ao menos um admin ativo válido
- [ ] Sessão administrativa curta com reautenticação
- [ ] PIN/biometria para telas administrativas no app

## 4. Hardening
- [ ] Criptografia de dados em repouso ativa
- [ ] Logs de eventos críticos com trilha auditável
- [ ] Plano de atualização de dependências
- [ ] Plano de resposta a incidentes e recuperação

## Prioridade de Correção
1. Crítico: credenciais padrão, segredos expostos, falta de autenticação em ação sensível.
2. Alto: integrações ativas sem credenciais completas, ausência de trilha de auditoria.
3. Médio: configurações com risco operacional (wake word fraca, excesso de permissões).
4. Baixo: melhorias de observabilidade e automação de compliance.

## Comandos da Assistente
- `/auditoria` ou `varredura de segurança`
- `/varredura` ou `varredura do sistema`
