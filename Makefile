CONTAINER_RUNTIME ?= $(shell command -v podman 2>/dev/null || echo docker)
SKILLSAW_IMAGE = ghcr.io/stbenjam/skillsaw:0.14.0
SELINUX_OPT := $(shell if command -v getenforce >/dev/null 2>&1 && [ "$$(getenforce 2>/dev/null)" = "Enforcing" ]; then echo "--security-opt label=disable"; fi)

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: lint
lint: ## Lint all plugins with skillsaw (strict mode)
	$(CONTAINER_RUNTIME) run --rm --platform linux/amd64 $(SELINUX_OPT) -v $(PWD):/workspace:Z $(SKILLSAW_IMAGE) .

.PHONY: lint-pull
lint-pull: ## Pull the latest skillsaw image
	$(CONTAINER_RUNTIME) pull $(SKILLSAW_IMAGE)

.PHONY: update
update: ## Regenerate docs/ (run after any plugin change)
	$(CONTAINER_RUNTIME) run --rm --platform linux/amd64 $(SELINUX_OPT) -v $(PWD):/workspace:Z --entrypoint skillsaw $(SKILLSAW_IMAGE) docs -o docs/ --theme crimson-red

.DEFAULT_GOAL := help
