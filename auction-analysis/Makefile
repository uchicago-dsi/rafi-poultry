# Makefile for building and running the Streamlit Docker container

# Define variables for docker commands
DOCKER_BUILD_CMD = docker build -t streamlit-app .
DOCKER_RUN_CMD = docker run -v .:/app -p 8501:8501 streamlit-app

# Target for building the Docker image
build-streamlit:
	@echo "Building Streamlit Docker image..."
	@$(DOCKER_BUILD_CMD)

# Target for running the Docker container
run-streamlit:
	@echo "Running Streamlit Docker container on port 8501..."
	@$(DOCKER_RUN_CMD)