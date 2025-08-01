FROM python:3.13-slim

WORKDIR /app

# Install Node.js and npm for npx support
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv and uvx
RUN pip install uv
# Ensure uvx is available (it comes with uv)
RUN uv --version

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Copy frontend build if it exists
COPY frontend/dist ./frontend/dist

# Install the package in editable mode
RUN uv pip install --system -e .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Set environment variables
ENV DATABASE_URL="sqlite:////data/alpha_ai.db"

# Run the server
CMD ["python", "-m", "alpha_ai"]