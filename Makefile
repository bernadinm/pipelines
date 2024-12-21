CONTAINER_NAME=pipelines
IMAGE_NAME=ghcr.io/open-webui/pipelines:main
PORT=9099

# Define environment variables using pass
GOOGLE_API_KEY=$(shell pass aistudio.google.com/mbp-api-key)
GROQ_API_KEY=$(shell pass groq.com/mbp-api-key)
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
	ollama_pipeline \
	openai_manifold_pipeline \
	google_manifold_pipeline 

all: run

run: stop
	@echo "Starting container $(CONTAINER_NAME)..."
	@docker run -d \
		-p $(PORT):$(PORT) \
		--add-host=host.docker.internal:host-gateway \
		-e GOOGLE_API_KEY="$(GOOGLE_API_KEY)" \
		-e GROQ_API_KEY="$(GROQ_API_KEY)" \
		-e OPENAI_API_KEY="$(OPENAI_API_KEY)" \
		-e ANTHROPIC_API_KEY="$(ANTHROPIC_API_KEY)" \
		-e CLOUDFLARE_API_KEY="$(CLOUDFLARE_API_KEY)" \
		-e PERPLEXITY_API_KEY="$(PERPLEXITY_API_KEY)" \
		-e CLICKUP_API_TOKEN="$(CLICKUP_API_TOKEN)" \
		$(foreach volume,$(VOLUMES),-v $(CURDIR)/examples/pipelines/providers/$(volume).py:/app/pipelines/$(volume).py) \
		--name $(CONTAINER_NAME) \
		--restart always \
		$(IMAGE_NAME)

stop:
	@if [ $$(docker ps -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "Stopping existing container $(CONTAINER_NAME)..."; \
		docker stop $(CONTAINER_NAME); \
		docker rm $(CONTAINER_NAME); \
	fi

clean:
	@echo "Cleaning up Docker resources..."
	@if [ $$(docker ps -a -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "Removing container $(CONTAINER_NAME)..."; \
		docker rm -f $(CONTAINER_NAME); \
	fi
	@echo "Removing unused Docker images and volumes..."
	docker system prune -f

status:
	@echo "Checking the status of the container $(CONTAINER_NAME)..."
	@if [ $$(docker ps -q -f name=$(CONTAINER_NAME)) ]; then \
		echo "Container $(CONTAINER_NAME) is running."; \
	else \
		echo "Container $(CONTAINER_NAME) is not running."; \
	fi
