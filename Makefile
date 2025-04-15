# Makefile for the ADK Banking Bot

# Python setup
.PHONY: install
install:
	poetry install

.PHONY: lint
lint:
	poetry run flake8 .

.PHONY: format
format:
	poetry run black .

.PHONY: test
test:
	poetry run pytest

.PHONY: run
run:
	poetry run uvicorn app:app --host 0.0.0.0 --port 8000 --reload

.PHONY: docker
docker:
	docker build -t adk-banking-bot .

.PHONY: docker-run
docker-run:
	docker run -p 8000:8000 adk-banking-bot

.PHONY: lint-fix
lint-fix:
	poetry run black . && poetry run flake8 --max-line-length=100 .

.PHONY: deploy
deploy:
	# Example of deployment command (e.g., to AWS or GCP)
	echo "Deploying application..."