import os
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest
from fastapi import FastAPI
import uvicorn
from contextlib import asynccontextmanager

# =============================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# =============================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =============================
# НАСТРОЙКА БОТА
# =============================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8029678200:AAGxJLF_aidd4xCPdmzBYa9M0Y18WcJCBlo")

if not BOT_TOKEN:
    logger.error("❌ Токен бота не найден!")
    exit(1)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# =============================
# FastAPI приложение для Render
# =============================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Запуск при старте
    logger.info("🚀 Запуск бота...")
    
    # Запускаем бота в фоне
    asyncio.create_task(run_bot())
    
    yield
    
    # Очистка при остановке
    logger.info("🛑 Остановка бота...")
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Telegram bot is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# =============================
# Безопасное редактирование
# =============================
async def safe_edit_message(message: types.Message, text: str, reply_markup=None, parse_mode="Markdown"):
    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest as e:
        if "message is not modified" in e.message:
            pass
        elif "message to edit not found" in e.message:
            logger.warning("Сообщение для редактирования не найдено")
        else:
            logger.error(f"Ошибка редактирования: {e}")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")

# =============================
# ВАШ ОСНОВНОЙ КОД БОТА (без изменений)
# =============================

@dp.message(Command("start"))
async def start(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} запустил бота")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ЭЦП", callback_data="ecp_main")],
        [InlineKeyboardButton(text="Все для ЭЦП", callback_data="crypto_main")],
        [InlineKeyboardButton(text="Услуги по закупкам", callback_data="services_main")]
    ])
    await message.answer("Выберите раздел:", reply_markup=kb)

@dp.message(Command("help"))
async def help_command(message: types.Message):
    help_text = """
📚 **Доступные команды:**
/start - Главное меню
/help - Справка по боту
/status - Проверка работоспособности

🔍 **Разделы бота:**
1. ЭЦП - Выпуск электронных подписей для различных площадок
2. Все для ЭЦП - Ключи, лицензии и настройка
3. Услуги по закупкам - Сопровождение торгов

📞 **Техподдержка:**
Если возникли проблемы, обратитесь к администратору.
    """
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(Command("status"))
async def status_command(message: types.Message):
    await message.answer("✅ Бот работает исправно!")

# =============================
# БЛОК 1: ЭЦП (выпуск под площадки)
# =============================
ECPS_DATA = {
    "fl": [
        ("ftp", "ФТП", "Федеральные торговые площадки", "2800"),
        ("rosreestr_fl", "Росреестр (ФЛ)", "Для покупки квартиры", "2100"),
        ("epgu", "ЕПГУ", "Госуслуги и государственные порталы", "2100"),
        ("efrsfdyul", "ЕФРСФДЮЛ", "Федеральный ресурс юридических лиц", "2100"),
        ("fts", "ФТС", "Таможенная служба", "2100"),
        ("fts_alta", "ФТС Альта-Софт", "Таможня + программное обеспечение Альта-Софт", "4100"),
        ("egais", "ЕГАИС", "Учёт оборота алкогольной продукции", "2300"),
        ("rosreestr_ki", "Росреестр (кадастровый инженер)", "Подписание межевых и техпланов", "2100"),
        ("rosreestr_au", "Росреестр (арбитражный управляющий)", "Работа с делами о банкротстве", "2100"),
        ("rzd", "РЖД", "Электронная торговая площадка ОАО «РЖД»", "3300"),
        ("cdt", "ЦДТ", "Центр дистанционных торгов", "6800"),
        ("utender", "uTender", "Коммерческая ЭТП", "4600"),
        ("fabrikant", "Фабрикант", "Коммерческая ЭТП", "4000"),
        ("b2b", "B2B-Center", "Крупнейшая коммерческая площадка", "4000"),
        ("regtorg", "Регторг", "Коммерческая площадка", "4400"),
        ("uetp", "УЭТП", "Уральская ЭТП", "4400"),
        ("aist", "АИСТ", "Коммерческая ЭТП", "4600"),
        ("tender_ug", "Тендер ug", "Коммерческая площадка", "4800"),
        ("gpb", "ГПБ", "Закупки Газпромбанка", "5000"),
        ("alfalot", "Альфалот", "Коммерческая площадка", "4300"),
        ("atc", "Аукц. тендерный центр", "Коммерческая площадка", "3700"),
        ("center_real", "Центр реализации", "Продажа имущества (в т.ч. банкротство)", "2900"),
        ("etp_esp", "ЭТП ЭСП", "Поволжская площадка", "2900"),
        ("fis_frd", "ФИС ФРДО", "Для образовательных учреждений всех уровней", "2900"),
        ("crypto_embed", "Вшитая лицензия Крипто Про", "Дополнительно к ЭЦП", "+900"),
    ],
    "ip": [
        ("ip_note", "ИП", "Не выпускаем новые ЭЦП на ИП. Возможна только продление по действующей.", "1500"),
    ],
    "ul": [
        ("ul_note", "ООО / ЮЛ", "Не выпускаем новые ЭЦП на ООО. Возможна только продление по действующей.", "1500"),
    ]
}

ECPS_INFO = {}
for ecp_type in ECPS_DATA:
    for code, name, desc, price in ECPS_DATA[ecp_type]:
        ECPS_INFO[code] = {"name": name, "desc": desc, "price": price, "type": ecp_type}

@dp.callback_query(lambda c: c.data == "ecp_main")
async def ecp_main(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="Физическое лицо (ФЛ)", callback_data="ecp_type:fl")
    builder.button(text="Не выпускаем ЭЦП на ИП. Только продление по действующей", callback_data="ecp_type:ip")
    builder.button(text="Не выпускаем ЭЦП на ООО. Только продление по действующей", callback_data="ecp_type:ul")
    builder.button(text="← Назад", callback_data="back_to_main")
    builder.adjust(1)
    await safe_edit_message(callback.message, "Выберите тип организации:", reply_markup=builder.as_markup(), parse_mode=None)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("ecp_type:"))
async def ecp_choose_type(callback: types.CallbackQuery):
    ecp_type = callback.data.split(":")[1]
    titles = {"fl": "Физическое лицо", "ip": "ИП", "ul": "ООО / Юридическое лицо"}
    builder = InlineKeyboardBuilder()
    for code, name, desc, price in ECPS_DATA[ecp_type]:
        builder.button(text=f"{name} — {price} ₽", callback_data=f"ecp_show:{code}")
    builder.button(text="← Назад", callback_data="ecp_main")
    builder.adjust(1)
    await safe_edit_message(
        callback.message,
        f"ЭЦП для: {titles[ecp_type]}\nВыберите назначение:",
        reply_markup=builder.as_markup(),
        parse_mode=None
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("ecp_show:"))
async def ecp_show_details(callback: types.CallbackQuery):
    code = callback.data.split(":")[1]
    info = ECPS_INFO.get(code)
    if not info:
        await callback.answer("Неизвестная ЭЦП", show_alert=True)
        return
    text = f"📄 **{info['name']}**\n\n{info['desc']}\n\nСтоимость: **{info['price']} ₽**"
    builder = InlineKeyboardBuilder()
    builder.button(text="← Назад", callback_data=f"ecp_type:{info['type']}")
    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()

# =============================
# БЛОК 2: Все для ЭЦП (аппаратура и ПО)
# =============================
CRYPTO_ITEMS = [
    ("rt_lite", "Рутокен Lite", "Носитель ЭЦП начального уровня", "2000 ₽"),
    ("rt_3", "Рутокен 3.0", "Носитель ЭЦП с расширенными возможностями", "2700 ₽"),
    ("cp_15", "Крипто Про (15 мес.)", "Лицензия на СКЗИ КриптоПро на 15 месяцев", "2050 ₽"),
    ("cp_life", "Крипто Про (бессрочная)", "Бессрочная лицензия", "3600 ₽"),
    ("cp_arm", "Крипто АРМ (бессрочная)", "Лицензия для подписания документов ЭЦП", "4000 ₽"),
    ("pc_setup", "Настройка ПК под ЭЦП", "Установка драйверов, КриптоПро, тестирование. Настройка ПК по удаленному доступу, либо у нас в офисе", "2500 ₽"),
]

CRYPTO_INFO = {}
for code, name, desc, price in CRYPTO_ITEMS:
    CRYPTO_INFO[code] = {"name": name, "desc": desc, "price": price}

@dp.callback_query(lambda c: c.data == "crypto_main")
async def crypto_main(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for code, name, desc, price in CRYPTO_ITEMS:
        builder.button(text=f"{name} — {price}", callback_data=f"crypto_show:{code}")
    builder.button(text="← Назад", callback_data="back_to_main")
    builder.adjust(1)
    await safe_edit_message(
        callback.message,
        "🔐 **Все для ЭЦП**\nАппаратные ключи, лицензии и настройка:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("crypto_show:"))
async def crypto_show_details(callback: types.CallbackQuery):
    code = callback.data.split(":")[1]
    info = CRYPTO_INFO.get(code)
    if not info:
        await callback.answer("Товар не найден", show_alert=True)
        return
    text = f"🔐 **{info['name']}**\n\n{info['desc']}\n\nСтоимость: **{info['price']}**"
    builder = InlineKeyboardBuilder()
    builder.button(text="← Назад", callback_data="crypto_main")
    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()

# =============================
# БЛОК 3: Услуги по закупкам (без ЭЦП!)
# =============================
PROCUREMENTS = {
    "44fz": [
        ("base_44", "Базовое сопровождение по 44-ФЗ", "Полное оформление закупки: от подготовки заявки до подписания контракта. 1. Подготовка заявки 2. Подача заявки 3. Проведение аукциона 4. Подписание контракта", "от 7000 ₽"),
        ("pp2571", "Подтверждение опыта по ПП 2571", "Прохождение аккредитации на 1 ЭТП для подтверждения опыта", "3000 ₽"),
        ("struct_menu", "Структурированная форма закупки", "Анализ и заполнение показателей структуры", "см. подменю"),
        ("urgent_44", "Срочность (<1 дня)", "Оформление заявки менее чем за 1 рабочий день до окончания подачи", "+3000 ₽"),
        ("93_12", "Закупка по ч.12 ст.93", "Закупка единственного поставщика по 44-ФЗ. Размещение предложения на ЭТП", "от 5000 ₽"),
    ],
    "223fz": [
        ("base_223", "Базовое сопровождение по 223-ФЗ", "Полное сопровождение закупки. 1. Подготовка заявки 2. Подача заявки 3. Проведение аукциона 4. Подписание контракта", "от 10000 ₽"),
        ("urgent_223", "Срочность", "Ускоренное оформление", "+3000 ₽"),
    ],
    "com": [
        ("base_com", "Коммерческие торги", "Подготовка заявки на коммерческих ЭТП. 1. Подготовка заявки 2. Подача заявки 3. Проведение аукциона 4. Подписание контракта", "от 10000 ₽"),
        ("urgent_com", "Срочность", "Ускоренное оформление", "+3000 ₽"),
    ],
    "bankrot": [
        ("base_bankrot", "Имущественные торги / банкротство", "Подготовка и подача заявки на торги по продаже и аренде имущества. 1. Подготовка заявки 2. Подача заявки 3. Проведение аукциона 4. Подписание контракта", "от 9000 ₽"),
        ("urgent_bankrot", "Срочность", "Ускоренное оформление", "+3000 ₽"),
    ],
    "bereza": [
        ("bereza", "Электронный магазин", "Подача предложения на Березка, Мос.рег.ру и др.. 1. Подача предложения 2. Подписание контракта", "3500 ₽"),
    ],
    "seldon": [
        ("seldon_3", "Поиск торгов (3 мес.)", "Рассылка актуальных закупок по вашим критериям. Рассылка Селдон по ключевым словам, областям", "6000 ₽"),
        ("seldon_6", "Поиск торгов (6 мес.)", "Подписка на полгода. Рассылка Селдон по ключевым словам, областям", "9000 ₽"),
        ("seldon_9", "Поиск торгов (9 мес.)", "Подписка на 9 месяцев. Рассылка Селдон по ключевым словам, областям", "12 000 ₽"),
        ("seldon_12", "Поиск торгов (12 мес.)", "Годовая подписка. Рассылка Селдон по ключевым словам, областям", "15 000 ₽"),
        ("seldon_edit", "Изменение анкеты Селдон (>3 раз)", "Дополнительные правки после 3 бесплатных", "1000 ₽"),
    ]
}

STRUCTURE_ITEMS = [
    ("struct_1_40", "Показатели 1–40", "Анализ и заполнение до 40 показателей", "+2500 ₽"),
    ("struct_41_80", "Показатели 41–80", "Анализ и заполнение до 80 показателей", "+3500 ₽"),
    ("struct_81_120", "Показатели 81–120", "Анализ и заполнение до 120 показателей", "+5000 ₽"),
    ("struct_121_160", "Показатели 121–160", "Анализ и заполнение до 160 показателей", "+7000 ₽"),
]

OTHER_SERVICES = {
    "reg": [
        ("eruz", "Регистрация в ЕРУЗ", "Получение аккредитации в Едином реестре участников закупок", "5500 ₽"),
        ("com_plat", "Регистрация на коммерческой площадке", "Аккредитация на одной коммерческой ЭТП", "от 5000 ₽"),
        ("dop_one", "Доп. требования (1 площадка)", "Прохождение доп. аккредитации на одной площадки", "3000 ₽"),
        ("dop_all", "Доп. требования (все площадки)", "Прохождение доп. аккредитации на всех площадках (8 Федеральный торговых площадок)", "7500 ₽"),
    ],
    "complex": [
        ("complex_1", "Комплексное сопровождение (1 мес.)", "Полное сопровождение всех закупок клиента в течение месяца. 1. Максимум 20 Закопок за месяц 2. Делаем МЧД для участия в торгах 3. Проходим регистрацию на коммерческих площадках по присланным закупкам", "25 000 ₽ + 1%"),
        ("complex_6", "Комплексное сопровождение (6 мес.)", "Ежемесячная абонентская поддержка. 1. Максимум 20 Закопок в месяц 2. Делаем МЧД для участия в торгах 3. Выпускае ЭЦП 4. Проходим регистрацию на коммерческих площадках по присланным закупкам 5. Рассылка тендеров", "20 000 ₽/мес + 1%"),
    ],
    "other": [
        ("act", "Электронное актирование", "Подписание актов по заключённым контрактам", "2500 ₽"),
        ("mchd", "МЧД", "Выдача машиночитаемой доверенности. В основном для торгов, но можем сделать любую", "1500 ₽"),
        ("trade_long", "Участие в торгах (>5 часов)", "Сопровождение длительных торгов", "1500 ₽/час (раб.), 7000 ₽/час (нераб.)"),
        ("ast_gos", "АСТ-ГОЗ (гособоронзаказ)", "Получение доступа и настройка ПК для гособоронзаказа", "15 000 ₽"),
        ("etprf_gpb", "ETPRF.RU / Специализированная на ГПБ", "Получение доступа к закрытым площадкам", "12 000 ₽"),
        ("fas", "Жалоба в ФАС", "Подготовка и подача жалобы на действия заказчика", "от 15 000 ₽"),
        ("consult", "Консультации", "Индивидуальная консультация по закупкам и юридическим вопросам", "от 2000 ₽"),
    ]
}

# Собираем все услуги для деталей
ALL_SERVICES = {}
for cat, items in PROCUREMENTS.items():
    for code, name, desc, price in items:
        ALL_SERVICES[code] = {"name": name, "desc": desc, "price": price, "cat": cat}
for code, name, desc, price in STRUCTURE_ITEMS:
    ALL_SERVICES[code] = {"name": name, "desc": desc, "price": price, "cat": "structure"}
for cat in OTHER_SERVICES:
    for code, name, desc, price in OTHER_SERVICES[cat]:
        ALL_SERVICES[code] = {"name": name, "desc": desc, "price": price, "cat": cat}

@dp.callback_query(lambda c: c.data == "services_main")
async def services_main(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.button(text="44-ФЗ", callback_data="proc:44fz")
    builder.button(text="223-ФЗ", callback_data="proc:223fz")
    builder.button(text="Коммерческие торги", callback_data="proc:com")
    builder.button(text="Имущественные торги / банкротство", callback_data="proc:bankrot")
    builder.button(text="Электронные магазины (Березка и др.)", callback_data="proc:bereza")
    builder.button(text="🔍 Поиск торгов", callback_data="proc:seldon")
    builder.button(text="Регистрация (ЕРУЗ, площадки)", callback_data="svc:reg")
    builder.button(text="Комплексное сопровождение", callback_data="svc:complex")
    builder.button(text="Прочее (жалобы, МЧД и др.)", callback_data="svc:other")
    builder.button(text="← Назад", callback_data="back_to_main")
    builder.adjust(1)
    await safe_edit_message(
        callback.message,
        "Выберите тип закупок или услугу:",
        reply_markup=builder.as_markup(),
        parse_mode=None
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("proc:"))
async def show_proc_list(callback: types.CallbackQuery):
    cat = callback.data.split(":")[1]
    titles = {
        "44fz": "44-ФЗ",
        "223fz": "223-ФЗ",
        "com": "Коммерческие торги",
        "bankrot": "Имущественные торги / банкротство",
        "bereza": "Электронные магазины",
        "seldon": "🔍 Поиск торгов",
    }
    builder = InlineKeyboardBuilder()
    for code, name, desc, price in PROCUREMENTS[cat]:
        if code == "struct_menu":
            builder.button(text=name, callback_data="struct_menu")
        else:
            builder.button(text=f"{name} — {price}", callback_data=f"svc_show:{code}")
    builder.button(text="← Назад", callback_data="services_main")
    builder.adjust(1)
    await safe_edit_message(
        callback.message,
        f"📋 **{titles[cat]}**",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "struct_menu")
async def show_structure_menu(callback: types.CallbackQuery):
    builder = InlineKeyboardBuilder()
    for code, name, desc, price in STRUCTURE_ITEMS:
        builder.button(text=f"{name} — {price}", callback_data=f"svc_show:{code}")
    builder.button(text="← Назад", callback_data="proc:44fz")
    builder.adjust(1)
    await safe_edit_message(
        callback.message,
        "📊 **Структура закупки (44-ФЗ)**\nВыберите блок показателей:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

SERVICE_TITLES = {
    "reg": "Регистрация",
    "complex": "Комплексное сопровождение",
    "other": "Прочие услуги"
}

@dp.callback_query(lambda c: c.data.startswith("svc:") and not c.data.startswith("svc_show:"))
async def show_other_services(callback: types.CallbackQuery):
    cat = callback.data.split(":")[1]
    builder = InlineKeyboardBuilder()
    for code, name, desc, price in OTHER_SERVICES[cat]:
        builder.button(text=f"{name} — {price}", callback_data=f"svc_show:{code}")
    builder.button(text="← Назад", callback_data="services_main")
    builder.adjust(1)
    await safe_edit_message(
        callback.message,
        f"📋 **{SERVICE_TITLES[cat]}**",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("svc_show:"))
async def show_service_details(callback: types.CallbackQuery):
    code = callback.data.split(":")[1]
    info = ALL_SERVICES.get(code)
    if not info:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    text = f"💼 **{info['name']}**\n\n{info['desc']}\n\nСтоимость: **{info['price']}**"
    builder = InlineKeyboardBuilder()
    cat = info["cat"]
    if cat == "structure":
        back_data = "struct_menu"
    elif cat in PROCUREMENTS:
        back_data = f"proc:{cat}"
    else:
        back_data = f"svc:{cat}"
    builder.button(text="← Назад", callback_data=back_data)
    await safe_edit_message(callback.message, text, reply_markup=builder.as_markup())
    await callback.answer()

# =============================
# НАВИГАЦИЯ
# =============================
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await start(callback.message)
    await callback.answer()

# =============================
# ФУНКЦИЯ ЗАПУСКА БОТА
# =============================
async def run_bot():
    try:
        logger.info("🤖 Запуск Telegram бота...")
        me = await bot.get_me()
        logger.info(f"✅ Бот @{me.username} успешно запущен!")
        logger.info(f"👤 Имя бота: {me.full_name}")
        
        # Запускаем поллинг
        await dp.start_polling(bot, skip_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Ошибка в работе бота: {e}")
        logger.info("🔄 Перезапуск через 10 секунд...")
        await asyncio.sleep(10)
        # Перезапускаем бота
        asyncio.create_task(run_bot())

# =============================
# ЗАПУСК СЕРВЕРА ДЛЯ RENDER
# =============================
if __name__ == "__main__":
    # Получаем порт от Render (если есть)
    port = int(os.getenv("PORT", 8000))
    
    logger.info(f"🌐 Запуск веб-сервера на порту {port}")
    
    # Запускаем сервер
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

