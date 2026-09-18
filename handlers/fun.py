"""Фан-команды: roast, diss, anekdot, klichka, mudrost, hvala."""
import random
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from brain.ollama import one_shot
from handlers.start import get_mode

router = Router()

DISS_LIST = [
    "Ты такой тупой, что даже Wi-Fi от тебя уходит, {name} 🤣",
    "Слушай, {name}, у тебя лицо как понедельник — никто не рад, но приходится терпеть 💩",
    "Ты не лох, ты — коллекционное издание лоха, {name} 🔥",
    "Твой мозг как вклад в банке — вроде есть, а снять нихуя нельзя, {name}",
    "Ты как реклама на ютубе — всех заебал, а пропустить нельзя, {name} 🤣",
    "У тебя харизма как у мокрого носка, {name} 💩",
    "Ты настолько душный, что кондиционер тебе завидует, {name}",
    "Если бы тупость светилась, ты бы, {name}, был маяком, бля 🔥",
    "Твои шутки как твоя борода — жидкие и жалкие, {name}",
    "Ты как понедельник в пятницу — никому нахуй не нужен, {name} 🤣",
]

ANEKDOT_LIST = [
    "— Доктор, я себя плохо чувствую.\n— А вы бухать меньше пробовали?\n— Пробовал, чувствую себя ещё хуже — скучно, бля.",
    "Идёт медведь по лесу, видит — мужик без лыж. Ну и доебался, конечно. Мораль: нехуй без лыж по лесу шляться.",
    "— Алё, это дурка?\n— Нет, это Вася. Но ты почти угадал 🤣",
    "Штирлиц долго смотрел в одну точку. Потом точка посмотрела на Штирлица и послала его нахуй.",
    "— Ты кем работаешь?\n— Лохом.\n— А платят хорошо?\n— Не, но стабильно.",
    "Купил мужик резиновую бабу. А она ему и говорит: «Ты чё, самый умный? Я надувная, а ты — нет» 💩",
    "— Бабушка, а почему у тебя такие большие зубы?\n— Потому что я Вася в душе, внучок 🔥",
    "Заходит улитка в бар... через 3 года. Бармен: «Ты где была?» Улитка: «Ты чё доебался, торопилась как могла, бля».",
]

MUDROST_LIST = [
    "Если жизнь дала тебе лимоны — продай их и купи семки, чё как лох-то? 🍋",
    "Не ссы против ветра и не спорь с Васям. Два главных правила жизни 💩",
    "Умный в гору не пойдёт, умный гору пошлёт нахуй и поедет на такси.",
    "Кто рано встаёт — тот всех заебал. Спи, еблан, ты красавчик 🔥",
    "Деньги — не главное. Главное — чтобы их дохуя было.",
    "Не откладывай на завтра то, что можно проебать сегодня.",
    "Скромность украшает. Поэтому я, бля, как новогодняя ёлка сияю 🤣",
]

HVALA_LIST = [
    "Ты молодец, {name}! Почти не тупил сегодня. Так держать, мой маленький прогрессирующий еблан 🤣",
    "Красава, {name}! Мозг включил, аж свет в подъезде мигнул 🔥",
    "Уважаю, {name}. Тупишь стабильно, но с огоньком 💩",
    "Ты сегодня неплох, {name}. Для тебя это прям подвиг, горжусь, еблан 🤣",
]


def target_name(m: Message) -> str:
    if m.reply_to_message and m.reply_to_message.from_user:
        return m.reply_to_message.from_user.first_name or "чел"
    parts = (m.text or "").split(maxsplit=1)
    if len(parts) > 1 and parts[1].strip():
        return parts[1].strip()[:50]
    return (m.from_user.first_name if m.from_user else None) or "чел"


@router.message(Command("diss"))
async def diss(m: Message):
    name = target_name(m)
    # 50/50: локальный или через ИИ
    if random.random() < 0.5:
        await m.answer(random.choice(DISS_LIST).format(name=name))
    else:
        txt = await one_shot(
            f"Доебись до чела по имени {name} одной жёсткой смешной строкой с матом, до 25 слов.",
            mode=get_mode(m.chat.id),
        )
        await m.answer(txt, parse_mode=None)


@router.message(Command("anekdot"))
async def anekdot(m: Message):
    if random.random() < 0.6:
        await m.answer("Держи, еблан:\n\n" + random.choice(ANEKDOT_LIST))
    else:
        txt = await one_shot(
            "Расскажи короткий дерзкий русский анекдот с матом, до 60 слов, смешной, не баян.",
            mode=get_mode(m.chat.id),
        )
        await m.answer(txt, parse_mode=None)


@router.message(Command("mudrost"))
async def mudrost(m: Message):
    if random.random() < 0.5:
        await m.answer("Мудрость дня, записывай, лох:\n\n<i>" + random.choice(MUDROST_LIST) + "</i>")
    else:
        txt = await one_shot(
            "Придумай одну мудрость дня в стиле гопника-философа с матом, смешную, до 30 слов.",
            mode=get_mode(m.chat.id),
        )
        await m.answer(txt, parse_mode=None)


@router.message(Command("hvala", "hvaleb", "pohvala"))
async def hvala(m: Message):
    name = target_name(m)
    if random.random() < 0.5:
        await m.answer(random.choice(HVALA_LIST).format(name=name))
    else:
        txt = await one_shot(
            f"Похвали чела по имени {name}, но через издёвку и подкол, с матом, смешно, до 30 слов.",
            mode=get_mode(m.chat.id),
        )
        await m.answer(txt, parse_mode=None)


@router.message(Command("roast"))
async def roast(m: Message):
    name = target_name(m)
    extra = ""
    if m.reply_to_message and m.reply_to_message.text:
        extra = f" Его сообщение для основы: «{m.reply_to_message.text[:300]}»"
    elif len((m.text or "").split(maxsplit=1)) > 1:
        extra = f" Про него известно: «{(m.text or '').split(maxsplit=1)[1][:300]}»"

    await m.bot.send_chat_action(m.chat.id, "typing")
    txt = await one_shot(
        f"Разнеси в хлам чела по имени {name}. Жёсткий roast, 2-4 предложения, с матом, кличками и чёрным юмором, очень смешно.{extra} "
        "В конце предложи реванш.",
        mode=get_mode(m.chat.id),
    )
    await m.answer(txt, parse_mode=None)


@router.message(Command("klichka", "klicha", "nick"))
async def klichka(m: Message):
    name = target_name(m)
    await m.bot.send_chat_action(m.chat.id, "typing")
    txt = await one_shot(
        f"Придумай для чела по имени {name} 3 обидные смешные клички с объяснением почему, с матом, до 50 слов.",
        mode=get_mode(m.chat.id),
    )
    await m.answer(txt, parse_mode=None)
