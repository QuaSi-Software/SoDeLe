# Instruction for RUDI-API

---

## Pre Requirements

- Install [Docker] https://docs.docker.com/install/
- Install [Docker compose] https://docs.docker.com/compose/install/
- Before building, make sure to copy the .env.template file to .env and make adjustemnts to the env variables, if needed

## Basic Commands

### Initial Setup
- start the API with: ```docker compose up -d api```

In order to stop the containers, use the following command: ```docker compose down```

### Install new Requirements

Sometimes it can happen, that new requirements are added to the project, in this case, do the following:

- stop the API with: ```docker compose stop api```
- build the API with: ```docker compose build api```
- start the API with: ```docker compose up -d api```

## Initialize project as your development environment

You can initialize the project as your developement environment, by doing the following:

- start and build container with: ```docker-compose up -d```
- shut down container with: ```docker-compose down```

## Ports explanation

- 5010: api (server)

---