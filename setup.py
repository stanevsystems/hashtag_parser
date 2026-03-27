#!/usr/bin/env python3
"""
Универсальный скрипт настройки окружения для Telegram Hashtag Collector (Telethon)
Поддерживает: Windows, macOS, Linux
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(cmd: list, description: str):
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ Успешно")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка: {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print("❌ Команда не найдена. Убедитесь, что Python установлен.")
        return False

def main():
    print("🚀 Настройка окружения для Telegram Hashtag Parser")
    print(f"Платформа: {platform.system()} {platform.release()}\n")

    # 1. Проверка Python
    python_version = sys.version_info
    if python_version < (3, 9):
        print(f"⚠️ Рекомендуется Python 3.9+, у вас {python_version.major}.{python_version.minor}")
    else:
        print(f"✅ Python {python_version.major}.{python_version.minor} — подходит")

    # 2. Создание виртуального окружения
    venv_path = Path("venv")
    if not venv_path.exists():
        print("\n📦 Создаём виртуальное окружение...")
        if not run_command([sys.executable, "-m", "venv", "venv"], "Создание venv"):
            sys.exit(1)
    else:
        print("✅ Виртуальное окружение уже существует")

    # 3. Активация и установка пакетов
    print("\n📥 Устанавливаем необходимые пакеты...")

    if platform.system() == "Windows":
        pip_cmd = [".\\venv\\Scripts\\pip.exe", "install", "--upgrade"]
    else:
        pip_cmd = ["./venv/bin/pip", "install", "--upgrade"]

    packages = ["telethon", "python-dotenv", "pysocks"]

    if not run_command(pip_cmd + ["pip", "setuptools", "wheel"], "Обновление pip и инструментов"):
        print("⚠️ Продолжаем установку пакетов...")

    if not run_command(pip_cmd + packages, "Установка Telethon + зависимостей"):
        print("❌ Не удалось установить пакеты. Проверьте интернет и прокси.")
        sys.exit(1)

    # 4. Создание .env.example (если нет .env)
    env_example = Path(".env.example")
    if not env_example.exists():
        env_content = """# Telegram API credentials (получи на my.telegram.org)
api_id=1234567
api_hash=0123456789abcdef0123456789abcdef

# SOCKS5 прокси от v2rayN / Clash / Nekobox и т.д.
# На Windows/macOS чаще всего 10808 или 1080
proxy_type=socks5
proxy_host=127.0.0.1
proxy_port=10808
# proxy_username=
# proxy_password=
"""
        env_example.write_text(env_content, encoding="utf-8")
        print("✅ Создан .env.example — скопируй его в .env и заполни свои данные")

    # 5. Создание/обновление .gitignore
    gitignore = Path(".gitignore")
    git_content = """# Virtual Environment
venv/
__pycache__/
*.pyc

# Environment variables
.env

# Telethon session
*.session

# Output files
*.json
messages_*.json

# macOS
.DS_Store
"""
    if not gitignore.exists():
        gitignore.write_text(git_content, encoding="utf-8")
        print("✅ Создан .gitignore")
    else:
        print("✅ .gitignore уже существует")

    print("\n" + "="*60)
    print("🎉 Настройка завершена!")
    print("="*60)
    print("\nКак запустить бота:")

    if platform.system() == "Windows":
        print("   .\\venv\\Scripts\\activate")
        print("   python hashtag_parser.py")
    else:
        print("   source venv/bin/activate")
        print("   python hashtag_parser.py")

    print("\nНе забудь:")
    print("1. Скопировать .env.example → .env и заполнить api_id, api_hash и proxy_port")
    print("2. Запустить v2rayN / Clash / твой прокси-клиент")
    print("3. Проверить порт SOCKS5 (обычно 10808)")

if __name__ == "__main__":
    main()