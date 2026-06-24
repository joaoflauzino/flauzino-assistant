# Automating Raspberry Pi Deployments

## Objetivo
Automatizar os deploys da infraestrutura em um Raspberry Pi através de CI/CD utilizando GitHub Actions.

## Implementação
- Criação de uma action (GitHub Action) para escutar pushs na branch `main`.
- Configuração para executar comandos via self-hosted runner.
- Disparo do comando `docker-compose up` apontando para o arquivo `infra/rpi/docker-compose.yaml` quando houver mudanças.

## Status
Implementado.
