CONTAINER_NAME=pipelines
IMAGE_NAME=ghcr.io/open-webui/pipelines:main
PORT=9099

all: run

build:
	@echo "Using pre-built image $(IMAGE_NAME), skipping build step."

run: stop
	@echo "Starting container $(CONTAINER_NAME)..."
	docker run -d \
		-p $(PORT):$(PORT) \
		--add-host=host.docker.internal:host-gateway \
		-v $(CURDIR)/examples/pipelines/providers/anthropic_manifold_pipeline.py:/app/pipelines/anthropic_manifold_pipeline.py \
		-v $(CURDIR)/examples/pipelines/providers/perplexity_manifold_pipeline.py:/app/pipelines/perplexity_manifold_pipeline.py \
		-v $(CURDIR)/examples/pipelines/providers/cloudflare_ai_pipeline.py:/app/pipelines/cloudflare_ai_pipeline.py \
		-v $(CURDIR)/examples/pipelines/providers/groq_manifold_pipeline.py:/app/pipelines/groq_manifold_pipeline.py \
		-v $(CURDIR)/examples/pipelines/providers/ollama_pipeline.py:/app/pipelines/ollama_pipeline.py \
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
