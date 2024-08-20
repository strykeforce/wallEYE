# Useful Docker Commands

Run these as root.

`docker compose up --build`

`docker build --platform linux/arm64v8 .`

`docker save -o NAME.tar IMAGE`

`docker save IMAGE | gzip > NAME.tar`

`docker images`

`docker system prune -a --volumes`

`docker system prune -a`

`docker load < NAME.tar`