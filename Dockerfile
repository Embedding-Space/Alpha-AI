FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project files
COPY pyproject.toml ./
COPY src/ ./src/

# Install the package in editable mode
RUN uv pip install --system -e .

# Create data directory
RUN mkdir -p /data

# Expose port
EXPOSE 8000

# Set environment variables
ENV ALPHA_AI_DATABASE_URL="sqlite:////data/alpha_ai.db"

# Run the server
CMD ["python", "-m", "alpha_ai"]