.DEFAULT_GOAL := help

.PHONY: tar-source upgrade

tar-source: package-deps                                    ## Package repository as tar for easy distribution
	rm -rf tar-src/
	mkdir tar-src/
	git-archive-all --prefix template/ tar-src/template-v0.0.0.tar.gz

pre-commit-checks:                                          ## Run pre-commit-checks.
	pre-commit run --all-files

upgrade:                                                    ## Upgrade project dependencies
	pip-upgrade

help:                                                       ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
