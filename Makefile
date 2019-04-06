.PHONY: lint
lint:
	@echo "Starting  lint"
	find . -name "*.yml" | xargs yamllint -s
	#find . -name "*.py" | xargs pylint
	#find . -name "*.py" | xargs bandit
	@echo "Completed lint"
