# DASH Parser

A Flask-based application for DASH (Dynamic Adaptive Streaming over HTTP) parsing using Bento4 tools. This tool helps analyze and process DASH manifests and segments.

## Features

- Parse DASH MPD (Media Presentation Description) files
- Extract segment information
- Analyze bitrate ladders
- Support for multi-period DASH content
- Validate DASH manifests

## Prerequisites

- Docker

## Quick Start

1. Clone the repository:

```
git clone https://github.com/RupeshSatija/dash-parser
cd dash-parser
```


2. Build the Docker image:
docker build -t dash-parser .


3. Run the container:
bash
docker run -p 5000:5000 dash-parser



The application will be available at `http://localhost:5000`

## Docker Commands

- Build the image: `docker build -t dash-parser .`
- Run the container: `docker run -p 5000:5000 dash-parser`
- Stop the container: `docker stop <container_id>`
- Remove the container: `docker rm <container_id>`
- View logs: `docker logs <container_id>`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| FLASK_ENV | Environment (development/production) | production |
| FLASK_PORT | Port to run the application | 5000 |
| LOG_LEVEL | Logging level (DEBUG/INFO/WARNING/ERROR) | INFO |
