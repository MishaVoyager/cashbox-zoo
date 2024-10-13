import logging
from datetime import datetime
from typing import Any

from aiogram import Bot
from arq import cron

from configs.config import RedisConfig, Settings
from database import dbhelper, models
from helpers import texthelper, staffhelper, tghelper


async def notify_admins_about_dismissed_users(ctx: Any) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    models.init_engine()
    current_visitors = await models.Visitor.get_all()
    dismissed_visitors_emails = await staffhelper.get_dismissed_users_emails(6)
    dismissed_current_visitors = [i for i in current_visitors if i.email in dismissed_visitors_emails]
    if len(dismissed_current_visitors) == 0:
        return
    for visitor in dismissed_current_visitors:
        logging.warning(f"Среди пользователей бота есть уволенный сотрудник: {repr(visitor)}")
    header = "Внимание, среди пользователей бота есть уволенные сотрудники:"
    visitors_text = f"{header}\r\n\r\n{tghelper.render_visitors(dismissed_current_visitors)}"
    bot = Bot(token=Settings().token)
    admins = [i for i in current_visitors if i.is_admin and i.chat_id]
    for admin in admins:
        await bot.send_message(chat_id=admin.chat_id, text=visitors_text)
        logging.info(f"Админа {repr(admin)} уведомили об уволенных сотрудниках")


async def remind_about_return_time(ctx: Any) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    models.init_engine()
    bot = Bot(token=Settings().token)
    soon_expire_days = 1
    resources = await models.Resource.get_expiring(soon_expire_days)
    if len(resources) == 0:
        logging.info("Не найдено устройств, которые пора сдавать")
    for resource in resources:
        visitors = await models.Visitor.get_by_email(resource.user_email)
        if len(visitors) == 1 and visitors[0].chat_id is not None:
            expired_days_ago = datetime.now() - resource.return_date
            if expired_days_ago.days > 0:
                form = texthelper.get_word_ending(expired_days_ago.days, ["день", "дня", "дней"])
                reminder = f"Вы должны были вернуть устройство {expired_days_ago.days} {form} назад"
            elif expired_days_ago.days == 0:
                reminder = "Сегодня пора сдавать устройство"
            elif expired_days_ago.days * - 1 <= soon_expire_days:
                days_before_expire = expired_days_ago.days * - 1
                form = texthelper.get_word_ending(days_before_expire, ["день", "дня", "дней"])
                reminder = f"Через {days_before_expire} {form} пора сдавать устройство"
            else:
                continue
            chat_id = visitors[0].chat_id
            text = f"{reminder}: \r\n\r\n{await dbhelper.format_note(resource, chat_id)}"
            await bot.send_message(chat_id=chat_id, text=text)
            logging.info(f"Пользователя {repr(visitors[0])} уведомили о возврате устройства {repr(resource)}")


class WorkerSettings:
    redis_settings = RedisConfig().get_pool_settings()
    cron_jobs = [
        cron(
            name="remind_about_return_time",
            coroutine=remind_about_return_time,
            run_at_startup=False,
            keep_result=True,
            keep_result_forever=False,
            weekday={0, 1, 2, 3, 4},
            hour=7,
            minute=0
        ),
        cron(
            name="notify_admins_about_dismissed_users",
            coroutine=notify_admins_about_dismissed_users,
            run_at_startup=False,
            keep_result=True,
            keep_result_forever=False,
            weekday={0, 1, 2, 3, 4},
            hour=6,
            minute=0
        ),
    ]
