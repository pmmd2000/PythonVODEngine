# Python VOD Engine

Python VOD Engine is a project that uses Celery, RabbitMQ, Redis, and FFmpeg in its core to receive and convert videos to hls streams.

### Prerequisites

Make sure you have Docker and Docker Compose installed on your machine. If not, you can download and install them from the official Docker website:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/pmmd2000/PythonVODEngine.git
cd your-repository
```
To build and start the project, run:
```
docker-compose up -d --build
```

### Configuration:

You'll need you're own .env file to configure the connections, passwords,...
