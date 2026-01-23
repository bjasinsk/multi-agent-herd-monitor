FROM python:3.12-slim

RUN pip install uv

# copied readme because of [project] section in pyproject.toml
COPY aasd/pyproject.toml aasd/uv.lock aasd/README.md /app/aasd/
COPY aasd/pyproject.toml aasd/uv.lock /app/aasd/
WORKDIR /app/aasd
RUN uv pip install --system .
WORKDIR /app

# Copy requirements first for better caching
# COPY requirements.txt /app/
# RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

# Make scripts executable
# RUN chmod +x main.py examples.py monitor_states.py 

# Set default command
CMD ["python", "-u", "main.py"]
