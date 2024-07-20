.PHONY: list
list:
	@LC_ALL=C $(MAKE) -pRrq -f $(firstword $(MAKEFILE_LIST)) : 2>/dev/null | awk -v RS= -F: '/(^|\n)# Files(\n|$$)/,/(^|\n)# Finished Make data base/ {if ($$1 !~ "^[#.]") {print $$1}}' | sort | egrep -v -e '^[^[:alnum:]]' -e '^$@$$'

.PHONY: setup
setup:
	@poetry install
	@poetry run pre-commit install
	@poetry run pre-commit install-hooks

.PHONY: test
test:
	@JUPYTER_PLATFORM_DIRS=1 poetry run pytest tests -v --color yes


.PHONY: lint
lint:
	@poetry run mypy **/*.py --strict --ignore-missing-imports --no-warn-unused-ignores
	@poetry run isort **/*.py --profile black
	@poetry run ruff **/*.py --fix --line-length 120 --show-source -v
	@poetry run black **/*.py --line-length 120 --color
	@poetry run interrogate **/*.py -vv
