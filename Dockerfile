# Dockerfile for ADK Banking Bot

# Step 1: Use Python 3.10 as the base image
FROM python:3.10-slim

# Step 2: Set the working directory in the container
WORKDIR /app

# Step 3: Copy the poetry.lock and pyproject.toml into the container
COPY pyproject.toml poetry.lock /app/

# Step 4: Install Poetry (dependency manager) in the container
RUN pip install poetry

# Step 5: Install the dependencies using Poetry
RUN poetry install --no-dev --no-root

# Step 6: Copy the entire app into the container
COPY . /app/

# Step 7: Expose the port the app runs on
EXPOSE 8000

# Step 8: Define the command to run the application
CMD ["poetry", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]

