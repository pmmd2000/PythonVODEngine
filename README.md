# Python VOD Engine

It's a project that uses Celery, RabbitMQ, Redis, MSSQL and FFmpeg in its core to receive and convert videos to hls streams.

By default it's using two separate Dockerfiles from the same source to form flask and celery images, both of them can be up scaled horizantally, so your FFmpeg transcoding power and flask ingesting web server can be scaled infinitely.

It's using RabbitMQ as its connection broker and redis to store celery manifests and some cached data, the process will be entirely logged on MSSQL for further use.

### Prerequisites

Make sure you have Docker and Docker Compose installed on your machine. If not, you can download and install them from the official Docker website:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/pmmd2000/PythonVODEngine.git
```
To build and start the project, run:
```
docker-compose up -d --build
```

### Configuration:

You'll need you're own .env file to configure the connections, passwords,...
