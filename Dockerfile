# Use Bento4 as base image for DASH/HLS tools
FROM alfg/bento4:latest

# Install Python and pip using Alpine's package manager
# --no-cache flag prevents storing the package index locally
RUN apk add --no-cache \
    python3 \
    py3-pip

# Set the working directory in the container
WORKDIR /app

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 5000 for Flask application
EXPOSE 5000

# Start the Flask application
CMD ["python3", "-m", "flask", "run", "--host=0.0.0.0"] 