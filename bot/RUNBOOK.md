# Полный сценарий запуска (Hashtag Ideas Bot)

## Что это и как работает

1. **Telethon (user API)** — ваш аккаунт Telegram, не @BotFather-бот. Нужен доступ к истории группы.
2. Раз в N часов (по умолчанию 2) сканирует чат по `#япридумал`, дополняет `ideas.json`, пушит в GitHub по SSH.
3. Команды `/start`, `/stop`, `/interval`, `/sync` — пишете **себе** в «Избранное» или личку (от `TELEGRAM_ADMIN_IDS`).
4. **Прокси** обязателен, если `tnc 149.154.167.51 -Port 443` не проходит. v2rayN: mixed **10808**.

---

## Разово: подготовка

### 1. Telegram API

1. Откройте https://my.telegram.org/apps → войдите номером.
2. Создайте приложение (любое имя).
3. Скопируйте **App api_id** (число) и **App api_hash** (ровно 32 символа a–f, 0–9).
4. **Не** используйте токен BotFather и не путайте с «Test configuration» / MTProto на той же странице.

`ApiIdInvalidError` почти всегда значит: неверная пара id/hash, лишние кавычки в `.env`, или hash обрезан при копировании.

### 2. Файлы секретов

```
bot/
  .env                 ← API, CHAT_IDS, прокси (не в git)
  secrets/
    github_deploy_key  ← приватный deploy key GitHub (chmod 600)
  data/
    hashtag_bot_session.session   ← после --login
    state.json                    ← running, interval
    repo/                         ← клон telegram-ideas
```

**GitHub:** Settings → Deploy keys → Add → write access для `stanevsystems/telegram-ideas`.

### 3. ID для .env

| Переменная | Как узнать |
|------------|------------|
| `TELEGRAM_ADMIN_IDS` | @userinfobot — ваш user id |
| `CHAT_IDS` | id супергруппы `-100...` (@getidsbot / переслать сообщение) |

Аккаунт с которым логинитесь **должен быть в группе**.

---

## Локально на Windows (venv)

Python на машине нужен **только один раз** для `setup.ps1` (создать venv). Дальше — только `.\run.ps1`.

### Шаг A — окружение (один раз)

```powershell
cd D:\exchange\projects\_my_projects\hashtag_parser\bot
PowerShell -ExecutionPolicy Bypass -File .\setup.ps1
copy .env.example .env
# отредактировать .env
```

`setup.ps1` создаёт `venv\`, ставит `telethon`, `python-socks[asyncio]`, `python-dotenv`.

**Важно:** всегда запускайте **`.\run.ps1`**, не `python.exe main.py` из PATH — иначе старый Telethon и ошибки `.session`.

### Шаг B — v2rayN

- Режим: **Set system proxy** или mixed **10808**.
- Проверка: `tnc 127.0.0.1 -Port 10808` → `TcpTestSucceeded : True`.

В `.env`:

```env
USE_PROXY=true
PROXY_TYPE=socks5
PROXY_HOST=127.0.0.1
PROXY_PORT=10808
```

### Шаг C — проверка сети (без входа)

```powershell
.\run.ps1 --test
```

Ожидается: `Connection ... complete!` и либо `OK: Имя`, либо `Not authorized` + подсказка про `--login`.

### Шаг D — вход в Telegram (один раз, интерактивно)

```powershell
.\run.ps1 --login
```

Телефон `+79...`, код из Telegram. Появится `data\hashtag_bot_session.session`.

При `ApiIdInvalidError` — перепроверьте `.env` (см. раздел 1).

### Шаг E — рабочий запуск

```powershell
.\run.ps1
```

Окно держите открытым **или** используйте Docker (ниже) с `restart: unless-stopped`.

Через ~30 с — первая синхронизация, далее каждые `SYNC_INTERVAL_HOURS` часов.

**Остановка:** Ctrl+C или в Telegram: `/stop`. **Снова включить:** `/start` (бот должен быть запущен).

---

## Docker (без Python на хосте после сборки образа)

Нужны: **Docker Desktop** + на хосте **v2rayN** (прокси не в контейнере).

### Сборка образа

```powershell
cd D:\exchange\projects\_my_projects\hashtag_parser\bot
PowerShell -ExecutionPolicy Bypass -File .\docker\build.ps1
```

Linux/macOS: `sh docker/build.sh`

### Настройка перед запуском

1. `.env` на хосте в `bot/` (как локально).
2. `secrets/github_deploy_key` на хосте.
3. В Docker прокси на **хост** — в `docker-compose.yml` уже `PROXY_HOST=host.docker.internal` (перекрывает `.env` для контейнера).

### Первый вход (интерактив)

```powershell
.\docker\run.ps1 login
```

Создаст/обновит `data/hashtag_bot_session.session` на хосте (volume).

### Проверка

```powershell
.\docker\run.ps1 test
```

### Фоновый сервис

```powershell
.\docker\run.ps1 up
# логи
.\docker\run.ps1 logs
# стоп
.\docker\run.ps1 down
```

---

## Шпаргалка команд

| Действие | Локально (venv) | Docker |
|----------|-----------------|--------|
| Установка deps | `.\setup.ps1` | `.\docker\build.ps1` |
| Проверка сети/сессии | `.\run.ps1 --test` | `.\docker\run.ps1 test` |
| Вход (телефон+код) | `.\run.ps1 --login` | `.\docker\run.ps1 login` |
| Работа бота | `.\run.ps1` | `.\docker\run.ps1 up` |
| Управление в TG | `/start` `/stop` `/sync` `/interval 3` `/status` | то же |

---

## Частые проблемы

| Симптом | Решение |
|---------|---------|
| `proxy argument will be ignored` | `pip install "python-socks[asyncio]"` в **venv** |
| `unexpected keyword argument 'host'` | обновите код (`addr` в proxy) |
| `too many values to unpack` session | только `.\run.ps1`, не системный python |
| Таймаут 149.154.167.51 | прокси выключен или v2rayN не запущен |
| `ApiIdInvalidError` | id/hash с my.telegram.org/apps |
| Git push fail | deploy key в `secrets/`, `tnc github.com -Port 22` через прокси/git не нужен для SSH если 22 открыт |

---

## Нужно ли вручную запускать main?

- **Разработка / ПК всегда включён:** `.\run.ps1` вручную или автозагрузка (Планировщик заданий Windows → `run.ps1`).
- **Продакшен:** Docker `restart: unless-stopped` — после `login` и `up` перезапускает сам.
- **Не** нужно держать отдельный `--test` или `--login` в cron — только один процесс `main.py`.
