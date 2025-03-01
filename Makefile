CONTAINER_NAME=pipelines
IMAGE_NAME=ghcr.io/open-webui/pipelines:main
PORT=9099
LOG_LEVEL=info

# Define environment variables using pass
GOOGLE_API_KEY=$(shell pass aistudio.google.com/mbp-api-key)
GROQ_API_KEY=$(shell pass groq.com/mbp-api-key)
GROK_API_KEY=$(shell pass x.ai/mbp-api-key)
OPENAI_API_KEY=$(shell pass openai.com/Miguels-MBP/api-key)
ANTHROPIC_API_KEY=$(shell pass anthropic.com/mbp-api-key)
CLOUDFLARE_API_KEY=$(shell pass cloudflare.com/mbp-api-wokerai-api-key)
PERPLEXITY_API_KEY=$(shell pass perplexity.com/mbp-api-key)
CLICKUP_API_TOKEN=$(shell pass clickup.com/api-token)

VOLUMES = \
	anthropic_manifold_pipeline \
	perplexity_manifold_pipeline \
	cloudflare_ai_pipeline \
	groq_manifold_pipeline \
	grok_manifold_pipeline \
	ollama_pipeline \
	openai_manifold_pipeline \
	google_manifold_pipeline \
	youtube_search_pipe

# Colors for terminal output
GREEN=\033[0;32m
YELLOW=\033[0;33m
RED=\033[0;31m
NC=\033[0m # No Color

.PHONY: all run stop restart logs clean status help pull update

all: run

run: stop
	@echo "${GREEN}Starting container $(CONTAINER_NAME)...${NC}"
	@docker run -d \
		-p $(PORT):$(PORT) \
		--add-host=host.docker.internal:host-gateway \
		-e GOOGLE_API_KEY="$(GOOGLE_API_KEY)" \
		-e GROQ_API_KEY="$(GROQ_API_KEY)" \
		-e GROK_API_KEY="$(GROK_API_KEY)" \
		-e OPENAI_API_KEY="$(OPENAI_API_KEY)" \
		-e ANTHROPIC_API_KEY="$(ANTHROPIC_API_KEY)" \
		-e CLOUDFLARE_API_KEY="$(CLOUDFLARE_API_KEY)" \
		-e PERPLEXITY_API_KEY="$(PERPLEXITY_API_KEY)" \
		-e CLICKUP_API_TOKEN="$(CLICKUP_API_TOKEN)" \
		-e LOG_LEVEL="$(LOG_LEVEL)" \
		$(foreach volume,$(VOLUMES),-v $(CURDIR)/examples/pipelines/providers/$(volume).py:/app/pipelines/$(volume).py) \
		--name $(CONTAINER_NAME) \
		--restart always \
		$(IMAGE_NAME)
	@echo "${GREEN}Container started successfully. Access at http://localhost:$(PORT)${NC}"
	@echo "${YELLOW}Run 'make logs' to view container logs${NC}"

stop:
	@if [ $$(docker ps -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "${YELLOW}Stopping existing container $(CONTAINER_NAME)...${NC}"; \
		docker stop $(CONTAINER_NAME); \
		docker rm $(CONTAINER_NAME); \
		echo "${GREEN}Container stopped and removed${NC}"; \
	else \
		echo "${YELLOW}No running container named $(CONTAINER_NAME) found${NC}"; \
	fi

restart: stop run
	@echo "${GREEN}Container $(CONTAINER_NAME) restarted successfully${NC}"

logs:
	@echo "${YELLOW}Showing logs for container $(CONTAINER_NAME)...${NC}"
	@docker logs -f $(CONTAINER_NAME)

logs-tail:
	@echo "${YELLOW}Showing last 100 lines of logs for container $(CONTAINER_NAME)...${NC}"
	@docker logs --tail 100 -f $(CONTAINER_NAME)

clean:
	@echo "${YELLOW}Cleaning up Docker resources...${NC}"
	@if [ $$(docker ps -a -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "${YELLOW}Removing container $(CONTAINER_NAME)...${NC}"; \
		docker rm -f $(CONTAINER_NAME); \
		echo "${GREEN}Container removed${NC}"; \
	fi
	@echo "${YELLOW}Removing unused Docker images and volumes...${NC}"
	@docker system prune -f
	@echo "${GREEN}Cleanup complete${NC}"

status:
	@echo "${YELLOW}Checking the status of the container $(CONTAINER_NAME)...${NC}"
	@if [ $$(docker ps -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "${GREEN}Container $(CONTAINER_NAME) is running.${NC}"; \
		echo "Container ID: $$(docker ps -q -f name=$(CONTAINER_NAME))"; \
		echo "Created: $$(docker inspect -f '{{.Created}}' $(CONTAINER_NAME))"; \
		echo "Status: $$(docker inspect -f '{{.State.Status}}' $(CONTAINER_NAME))"; \
		echo "Health: $$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}N/A{{end}}' $(CONTAINER_NAME))"; \
		echo "Port mapping: $$(docker port $(CONTAINER_NAME))"; \
		echo "Image: $$(docker inspect -f '{{.Config.Image}}' $(CONTAINER_NAME))"; \
	else \
		echo "${RED}Container $(CONTAINER_NAME) is not running.${NC}"; \
	fi

pull:
	@echo "${YELLOW}Pulling latest image for $(IMAGE_NAME)...${NC}"
	@docker pull $(IMAGE_NAME)
	@echo "${GREEN}Image pulled successfully${NC}"

update: pull restart
	@echo "${GREEN}Container updated to latest image and restarted${NC}"

shell:
	@if [ $$(docker ps -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "${YELLOW}Opening shell in container $(CONTAINER_NAME)...${NC}"; \
		docker exec -it $(CONTAINER_NAME) /bin/sh; \
	else \
		echo "${RED}Container $(CONTAINER_NAME) is not running.${NC}"; \
	fi

help:
	@echo "${GREEN}Available commands:${NC}"
	@echo "  ${YELLOW}make${NC}              - Same as 'make run'"
	@echo "  ${YELLOW}make run${NC}          - Start the container"
	@echo "  ${YELLOW}make stop${NC}         - Stop the container"
	@echo "  ${YELLOW}make restart${NC}      - Restart the container"
	@echo "  ${YELLOW}make logs${NC}         - Show container logs (follow mode)"
	@echo "  ${YELLOW}make logs-tail${NC}    - Show last 100 lines of logs (follow mode)"
	@echo "  ${YELLOW}make status${NC}       - Check container status"
	@echo "  ${YELLOW}make clean${NC}        - Remove container and prune Docker resources"
	@echo "  ${YELLOW}make pull${NC}         - Pull the latest image"
	@echo "  ${YELLOW}make update${NC}       - Pull latest image and restart container"
	@echo "  ${YELLOW}make shell${NC}        - Open a shell in the running container"
	@echo "  ${YELLOW}make help${NC}         - Show this help message"
