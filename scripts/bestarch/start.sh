docker stop $(docker ps -q)
docker system prune --all --force --volumes
sudo chmod -R 777 ./grafanadata
docker compose -f docker-compose-bestartch.yml up -d