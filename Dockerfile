# Use an official Python runtime as a parent image
FROM python:3.11.13-slim

# Set the working directory in the container
WORKDIR /app

# Install uv
RUN pip install uv

# Copy the dependency files
COPY pyproject.toml uv.lock ./

# Create uv environment
RUN uv venv

# Install dependencies using uv
RUN uv pip sync --no-cache pyproject.toml

# Copy the rest of the application's code
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run main.py with uv when the container launches
CMD ["uv", "run", "main.py"]
