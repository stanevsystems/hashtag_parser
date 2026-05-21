# Hashtag Ideas Bot

Сканирует историю Telegram-чата по `#япридумал`, дополняет [telegram-ideas](https://github.com/stanevsystems/telegram-ideas) и пушит в GitHub.

**Полный сценарий запуска (локально + Docker):** [RUNBOOK.md](RUNBOOK.md)

## Быстрый старт (Windows)

```powershell
.\setup.ps1
# .env + secrets/github_deploy_key
.\run.ps1 --test
.\run.ps1 --login
.\run.ps1
```

## Docker

```powershell
.\docker\build.ps1
.\docker\run.ps1 login
.\docker\run.ps1 up
```

## Команды в Telegram (админ)

`/start` `/stop` `/interval 2` `/sync` `/status` `/help`
