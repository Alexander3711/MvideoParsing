import logging
import asyncio
import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Вставьте сюда ваш токен
BOT_TOKEN = "7338057696:AAGnNjK0nbCVQ9Va02aS5qFzZrHIOBmkNgU"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Словарь для красивых названий категорий с эмодзи
CATEGORY_NAMES = {
    'roboty-pylesosy': '🤖 Роботы-пылесосы',
    'vertikalnye-pylesosy': '💨 Вертикальные пылесосы',
    'feny': '💇‍♀️ Фены'
}

# Словарь с префиксами товаров для удаления, чтобы в кнопке было видно модель
PRODUCT_PREFIXES = {
    'roboty-pylesosy': [
        'Робот-пылесос для мытья полов',
        'Робот-пылесос'
    ],
    'vertikalnye-pylesosy': [
        'Пылесос ручной (handstick) моющий',
        'Пылесос ручной (handstick)'
    ],
    'feny': ['Фен']
}


def get_categories():
    """Сканирует папку data и возвращает отсортированный список категорий."""
    data_path = 'data'
    if not os.path.exists(data_path) or not os.path.isdir(data_path):
        return [], 'Папка `data` не найдена. Пожалуйста, сначала запустите парсер.'

    categories = []
    for folder_name in os.listdir(data_path):
        if os.path.isdir(os.path.join(data_path, folder_name)):
            result_file = os.path.join(data_path, folder_name, '4_category_result.json')
            if os.path.exists(result_file):
                try:
                    # Извлекаем ключ для словаря из имени папки
                    category_key = folder_name.split('_')[0]
                    # Получаем красивое имя из словаря или используем старый метод как запасной
                    category_display_name = CATEGORY_NAMES.get(category_key, category_key.replace('-', ' ').capitalize())
                    categories.append({'name': category_display_name, 'id': folder_name})
                except IndexError:
                    logger.warning(f"Пропущена папка с некорректным именем: {folder_name}")
                    continue

    if not categories:
        return [], 'В папке `data` нет обработанных категорий. Пожалуйста, запустите парсер.'

    return sorted(categories, key=lambda x: x['name']), None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет главное меню с категориями при команде /start."""
    categories, error_message = get_categories()
    if error_message:
        await update.message.reply_text(error_message)
        return

    keyboard = [
        [InlineKeyboardButton(cat['name'], callback_data=f"cat:{cat['id']}")]
        for cat in categories
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Здравствуйте! Выберите категорию:', reply_markup=reply_markup)


async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопку 'Назад' для возврата в главное меню."""
    query = update.callback_query
    await query.answer()

    categories, error_message = get_categories()
    if error_message:
        await query.edit_message_text(error_message)
        return

    keyboard = [
        [InlineKeyboardButton(cat['name'], callback_data=f"cat:{cat['id']}")]
        for cat in categories
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text('Выберите категорию:', reply_markup=reply_markup)


async def handle_category_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список товаров для выбранной категории."""
    query = update.callback_query
    await query.answer()

    # callback_data имеет формат "cat:category_folder_name"
    _, category_folder_name = query.data.split(':', 1)

    try:
        category_key = category_folder_name.split('_')[0]
    except IndexError:
        # Fallback, если имя папки не соответствует ожидаемому формату
        category_key = None

    result_file_path = os.path.join('data', category_folder_name, '4_category_result.json')

    try:
        with open(result_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        products = data.get('products', [])

        # Кнопки навигации и действий
        all_button = [InlineKeyboardButton("📦 Выгрузить все товары", callback_data=f"all:{category_folder_name}")]
        back_button = [InlineKeyboardButton("⬅️ Назад к категориям", callback_data="back_to_main")]

        if not products:
            await query.edit_message_text(
                "В этой категории нет товаров.",
                reply_markup=InlineKeyboardMarkup([back_button])
            )
            return

        # Создаем кнопки для каждого товара
        product_buttons = [all_button]
        for product in products:
            product_name = product.get('name', 'Без названия')
            product_id = product.get('productId')
            if product_id:
                # Умное сокращение названия для кнопки
                display_name = product_name
                if category_key:
                    # Сортируем префиксы по длине, чтобы сначала проверять более длинные
                    prefixes_to_remove = sorted(PRODUCT_PREFIXES.get(category_key, []), key=len, reverse=True)
                    for prefix in prefixes_to_remove:
                        if display_name.lower().startswith(prefix.lower() + ' '):
                            # Удаляем префикс (название категории) из названия товара
                            display_name = display_name[len(prefix):].lstrip()
                            break  # Префикс найден и удален, выходим из цикла

                # Обрезаем, если все еще слишком длинное, чтобы поместиться в кнопку
                # 64 байта - лимит, кириллица ~2 байта на символ. 30 * 2 = 60.
                display_name = (display_name[:30] + '…') if len(display_name) > 30 else display_name
                product_buttons.append([
                    InlineKeyboardButton(f"🛒 {display_name}", callback_data=f"prod:{category_folder_name}:{product_id}")
                ])

        product_buttons.append(back_button)
        reply_markup = InlineKeyboardMarkup(product_buttons)
        await query.edit_message_text("Выберите товар из списка или выгрузите все сразу:", reply_markup=reply_markup)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка при чтении файла для категории {category_folder_name}: {e}")
        await query.edit_message_text(
            "Не удалось загрузить товары для этой категории.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад к категориям", callback_data="back_to_main")]])
        )


async def handle_product_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет детальную информацию о выбранном товаре."""
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    # callback_data имеет формат "prod:category_folder_name:product_id"
    _, category_folder_name, product_id = query.data.split(':', 2)

    result_file_path = os.path.join('data', category_folder_name, '4_category_result.json')

    product_found = None
    try:
        with open(result_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for p in data.get('products', []):
            if p.get('productId') == product_id:
                product_found = p
                break
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка при поиске продукта {product_id} в {category_folder_name}: {e}")
        await context.bot.send_message(chat_id=query.message.chat_id, text="Произошла ошибка при поиске товара.")
        return

    if product_found:
        name = product_found.get('name', 'Без названия')
        base_price = product_found.get('item_basePrice', 'N/A')
        sale_price = product_found.get('item_salePrice', 'N/A')
        link = product_found.get('item_link', '#')

        message_text = (
            f"<b>{name}</b>\n\n"
            f"💰 Цена: {sale_price} ₽\n"
            f"<s>Старая цена: {base_price} ₽</s>\n\n"
            f"<a href='{link}'>🔗 Ссылка на товар</a>"
        )

        # Отправляем новое сообщение с информацией о товаре,
        # чтобы не заменять список товаров.
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message_text,
            parse_mode=constants.ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        await context.bot.send_message(chat_id=query.message.chat_id, text="Не удалось найти информацию по этому товару.")


async def handle_get_all_products(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет информацию по всем товарам в категории."""
    query = update.callback_query
    await query.answer()  # Подтверждаем нажатие кнопки

    # callback_data имеет формат "all:category_folder_name"
    _, category_folder_name = query.data.split(':', 1)

    try:
        category_key = category_folder_name.split('_')[0]
        category_display_name = CATEGORY_NAMES.get(category_key, category_key.replace('-', ' ').capitalize())
    except IndexError:
        category_display_name = "Выбранная категория"

    await context.bot.send_message(
        chat_id=query.message.chat_id,
        text=f"Начинаю выгрузку всех товаров из категории '{category_display_name}'. Это может занять некоторое время..."
    )

    result_file_path = os.path.join('data', category_folder_name, '4_category_result.json')

    try:
        with open(result_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        products = data.get('products', [])

        if not products:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"В категории '{category_display_name}' не найдено товаров."
            )
            return

        for product in products:
            name = product.get('name', 'Без названия')
            base_price = product.get('item_basePrice', 'N/A')
            sale_price = product.get('item_salePrice', 'N/A')
            link = product.get('item_link', '#')

            message_text = (
                f"<b>{name}</b>\n\n"
                f"💰 Цена: {sale_price} ₽\n"
                f"<s>Старая цена: {base_price} ₽</s>\n\n"
                f"<a href='{link}'>🔗 Ссылка на товар</a>"
            )

            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=message_text,
                parse_mode=constants.ParseMode.HTML,
                disable_web_page_preview=True
            )
            await asyncio.sleep(0.2)

        await context.bot.send_message(chat_id=query.message.chat_id, text=f"🎉 Выгрузка данных для категории '{category_display_name}' завершена.")

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Ошибка при чтении файла для категории {category_folder_name}: {e}")
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Произошла ошибка при обработке категории '{category_display_name}'. Попробуйте позже."
        )

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(back_to_main_menu, pattern="^back_to_main$"))
    application.add_handler(CallbackQueryHandler(handle_category_selection, pattern="^cat:"))
    application.add_handler(CallbackQueryHandler(handle_product_selection, pattern="^prod:"))
    application.add_handler(CallbackQueryHandler(handle_get_all_products, pattern="^all:"))

    logger.info("Бот запущен... Нажмите Ctrl+C для остановки.")
    application.run_polling()
    # Это сообщение будет выведено в лог, когда бот остановится
    logger.info("Бот остановлен.")

if __name__ == '__main__':
    main()
