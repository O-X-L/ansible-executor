install:
	pip install -r requirements.txt
	pip install -r requirements_build.txt
	pip install -r requirements_lint.txt
	pip install -r requirements_unit_test.txt

lint:
	bash scripts/lint.sh

test-integration:
	bash scripts/test_integration.sh

test-unit:
	bash scripts/test_unit.sh
