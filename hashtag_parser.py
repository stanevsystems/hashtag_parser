import asyncio
import json
from telethon import TelegramClient, events

# === НАСТРОЙКИ ===
# Получите api_id и api_hash здесь: https://my.telegram.org/apps
api_id = 1234567          # ← ВСТАВЬТЕ СВОЙ API_ID
api_hash = 'ваш_api_hash' # ← ВСТАВЬТЕ СВОЙ API_HASH

client = TelegramClient('hashtag_collector_session', api_id, api_hash)

@client.on(events.NewMessage(pattern=r'^/collect\s+(.+)'))
async def collect_hashtag(event):
    """Обработчик команды /collect #хэштег"""
    raw_tag = event.pattern_match.group(1).strip()
    hashtag = raw_tag if raw_tag.startswith('#') else f'#{raw_tag}'

    await event.reply(f'🔍 Ищу все сообщения с хэштегом **{hashtag}** в этом чате...\n'
                      f'Это может занять время при большом количестве сообщений.')

    messages = []
    try:
        # limit=None — собирает ВСЮ историю (Telegram позволяет до нескольких тысяч сообщений)
        # Если чат очень большой — можно поставить limit=2000
        async for message in client.iter_messages(
            event.chat_id,
            search=hashtag,      # поиск именно по тексту хэштега
            limit=None
        ):
            if message.text:  # берём только текстовые сообщения
                messages.append({
                    'date': message.date.isoformat(),
                    'sender_id': message.sender_id,
                    'message_id': message.id,
                    'text': message.text,
                    'link': f"https://t.me/c/{str(event.chat_id)[4:]}/{message.id}" if str(event.chat_id).startswith('-100') else None
                })
    except Exception as e:
        await event.reply(f'❌ Ошибка при поиске: {str(e)}')
        return

    if not messages:
        await event.reply(f'😔 Сообщений с хэштегом **{hashtag}** в истории чата не найдено.')
        return

    # Сохраняем в JSON-файл
    filename = f"messages_{hashtag.replace('#', '')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)

    # Отправляем результат
    await event.reply(
        f'✅ Найдено **{len(messages)}** сообщений с хэштегом **{hashtag}**.\n'
        f'Файл с полным списком прикреплён ниже.'
    )
    await client.send_file(
        event.chat_id,
        filename,
        caption=f'📁 Все сообщения с {hashtag} из истории чата'
    )

async def main():
    await client.start()
    print('✅ Бот запущен!')
    print('   Добавьте этот аккаунт в нужный чат и отправьте команду:')
    print('   /collect #вашхэштег')
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())