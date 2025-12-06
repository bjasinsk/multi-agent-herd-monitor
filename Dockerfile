FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Make scripts executable
RUN chmod +x main.py examples.py monitor_states.py

# Set default command
CMD ["python", "-u", "main.py"]
