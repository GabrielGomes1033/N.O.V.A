.PHONY: help quick quick-tests full apk

help:
	@echo "Comandos disponíveis:"
	@echo "  make quick        -> checagem rápida (backend compile + flutter analyze)"
	@echo "  make quick-tests  -> quick + flutter test"
	@echo "  make full         -> validação completa de integração"
	@echo "  make apk API_URL=https://sua-api -> build + install APK"

quick:
	@./scripts/quick_check.sh

quick-tests:
	@./scripts/quick_check.sh --tests

full:
	@./scripts/integration_check.sh

apk:
	@if [ -z "$(API_URL)" ]; then \
		echo "Uso: make apk API_URL=https://sua-api"; \
		exit 1; \
	fi
	@./scripts/build_and_install_apk.sh "$(API_URL)"
