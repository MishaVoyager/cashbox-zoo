import logging
from typing import Any

import emoji
from aiogram import Bot
from arq import cron

from configs.config import RedisConfig, Settings
from helpers import texthelper, staffhelper, tghelper
from helpers.presentation import format_note
from service.database_service import DatabaseService
from service.orm_uow import OrmUnitOfWork
from service.services import RecordService, VisitorService, ResourceService


async def notify_admins_about_dismissed_users(ctx: Any) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    uow = OrmUnitOfWork()
    db_service = DatabaseService(uow)
    visitor_service = VisitorService(uow)
    await db_service.init()
    get_result = await visitor_service.get_all()
    current_visitors = get_result.unwrap()
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


def get_reminder(will_be_expired_after: int) -> str:
    remind_emoji = emoji.emojize(':bell:')
    if will_be_expired_after < 0:
        if will_be_expired_after < -7:
            remind_emoji = emoji.emojize(':skull_and_crossbones:')
        else:
            remind_emoji = emoji.emojize(':red_exclamation_mark:')
        expired_days_ago = will_be_expired_after * -1
        form = texthelper.get_word_ending(expired_days_ago, ["день", "дня", "дней"])
        reminder = f"{remind_emoji} Вы должны были вернуть устройство {expired_days_ago} {form} назад"
    elif will_be_expired_after == 0:
        reminder = f"{remind_emoji} Сегодня пора сдавать устройство!"
    else:
        form = texthelper.get_word_ending(will_be_expired_after, ["день", "дня", "дней"])
        reminder = f"{remind_emoji} Через {will_be_expired_after} {form} пора сдавать устройство"
    return reminder


async def remind_about_return_time(ctx: Any) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )
    uow = OrmUnitOfWork()
    db_service = DatabaseService(uow)
    record_service = RecordService(uow)
    visitor_service = VisitorService(uow)
    resource_service = ResourceService(uow)

    await db_service.init()

    get_result = await record_service.get_expiring(1)
    expiring_records_dto = get_result.unwrap()
    bot = Bot(token=Settings().token)
    for dto in expiring_records_dto:
        reminder = get_reminder(dto.days_before_expire)
        get_visitor_result = await visitor_service.get(dto.record.user_email)
        visitor = get_visitor_result.unwrap()
        get_resource_result = await resource_service.get(dto.record.resource_id)
        resource = get_resource_result.unwrap()
        action_result = await record_service.get_available_action(resource.id, visitor.email)
        action = action_result.unwrap()
        text = f"{reminder}: \r\n\r\n{format_note(resource, visitor, action)}"
        await bot.send_message(chat_id=visitor.chat_id, text=text)
        logging.info(f"{repr(visitor)} уведомили о возврате устройства {repr(resource)}")


async def delete_old_records(ctx: Any) -> None:
    uow = OrmUnitOfWork()
    db_service = DatabaseService(uow)
    await db_service.init()
    record_service = RecordService(uow)
    await record_service.delete_old_finished_records(100)
    # TODO: Прикрутить уведомления для админа


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
        cron(
            name="delete_old_records",
            coroutine=delete_old_records,
            run_at_startup=False,
            keep_result=True,
            keep_result_forever=False,
            month={1, 4, 7, 10},
            day=1,
            hour=6,
            minute=0
        )
    ]
