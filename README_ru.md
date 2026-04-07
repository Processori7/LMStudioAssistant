# LM Studio Assistant для Flow Launcher

Плагин Flow Launcher на Python для локального API LM Studio.

## Возможности

- Общение с загруженными локальными моделями через `POST /api/v1/chat`
- Список моделей через `GET /api/v1/models`
- Загрузка и выгрузка моделей
- Запуск загрузки модели и проверка статуса загрузки
- Опциональный заголовок Bearer token (не обязателен для локальной незащищенной установки)

## Команды

Используйте ключевое слово `lm`.

- `lm models` (выберите модель и нажмите Enter, чтобы загрузить)
- `lm chat <prompt>`
- `lm chat <model_key> :: <prompt>`
- `lm load` (или `lm load <filter>`) затем Enter для загрузки выбранной модели
- `lm load! <model_key>` (загрузка модели по ключу напрямую)
- `lm unload! <instance_id>`
- `lm download! <model_or_hf_url>`
- `lm status` (показать загруженные модели и параметры контекста)
- `lm status <job_id>` (проверить статус загрузки)

Вы можете просто ввести `lm`, выбрать команду из списка и нажать Enter, чтобы автозаполнить её.

Для `lm chat` ответ модели отображается в результатах, а нажатие Enter копирует полный ответ.

## Настройки

Откройте настройки плагина в Flow Launcher и настройте:

- `baseUrl` по умолчанию: `http://localhost:1234`
- `apiToken` опционально (по умолчанию пусто)
- `defaultModel` ключ модели для чата без явного указания модели
- `systemPrompt` опционально
- `temperature` 0..1
- `maxOutputTokens` опционально, целое число
- `reasoning` off/low/medium/high/on
- `contextLength` опционально, целое число
- `timeoutSeconds` тайм-аут HTTP

## Установка

1. Поместите эту папку в `%APPDATA%\FlowLauncher\Plugins\LMStudioAssistant-1.0.0`.
2. Установите зависимости в этой папке: `pip install -r requirements.txt`.
3. Перезапустите Flow Launcher или выполните Reload Plugin Data.
4. Запустите плагин командой `lm`.

## Примечания

- LM Studio должно быть запущено с включенным локальным API.
- Если аутентификация отключена в LM Studio, оставьте `apiToken` пустым.
