.DEFAULT_GOAL := help

.PHONY: tar-source upgrade

tar-source: package-deps                                    ## Package repository as tar for easy distribution
	rm -rf tar/
	mkdir tar/
	git-archive-all --prefix collector-node/ tar/collector-node-v0.0.0.tar.gz

package-deps:                                               ## Upgrade dependencies for packaging
	python3 -m pip install -U twine wheel build git-archive-all

package-source: package-deps clean                          ## Package the source code
	python -m build .

clean:                                                      ## Clean the package directory
	rm -rf src/*.egg-info/
	rm -rf build/
	rm -rf dist/
	rm -rf tar-src/

pre-commit-checks:                                          ## Run pre-commit-checks.
	pre-commit run --all-files

upgrade:                                                    ## Upgrade project dependencies
	pip-upgrade

help:                                                       ## Print this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
