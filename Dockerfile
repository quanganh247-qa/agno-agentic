# Use the Python 3 alpine official image
# https://hub.docker.com/_/python
FROM python:3-alpine

# Create and change to the app directory.
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install project dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy local code to the container image.
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Run the web service on container startup with host 0.0.0.0
CMD ["uvicorn", "deep_research_fastapi:app", "--host", "0.0.0.0", "--port", "8000"]