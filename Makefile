.PHONY: build validate eval release-check

build:
	python3 scripts/build_creator_layers.py
	python3 scripts/build_database.py
	python3 scripts/sync_skill_data.py

validate:
	python3 scripts/validate.py
	python3 scripts/validate_skill.py

eval:
	python3 scripts/run_evals.py

release-check: build validate eval
	python3 scripts/release_check.py
