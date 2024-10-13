"""
Вспомогательные методы для выполнения сложных действий с БД и обработки данных
"""
import asyncio
import logging
from datetime import datetime
from io import StringIO
from typing import Optional, Any

import pandas as pd
from aiogram.types import Message, InlineKeyboardMarkup
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from database import models, resource_checker
from database.models import Resource, Visitor, Record, ActionType, Base, Action, CATEGORIES, Category
from handlers import strings
from handlers.strings import ResourceColumn
from helpers.tghelper import Paginator


async def get_wishlist(user: Visitor) -> list[Resource]:
    """Возвращает список ресурсов, за которыми пользователь стоит в очереди"""
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            stmt1 = select(Record).where(Record.user_email == user.email).where(
                Record.action == ActionType.QUEUE).with_only_columns(Record.resource)
            result1 = await session.scalars(stmt1)
            resource_ids = result1.all()
            stmt2 = select(Resource).filter(Resource.id.in_(resource_ids))
            result2 = await session.scalars(stmt2)
            resources = result2.all()
    return list(resources)


async def notify_user_about_return(message: Message, email: str, resource: Resource) -> None:
    """Уведомляет пользователя, что с него списали ресурс"""
    users: list[Visitor] = (await Visitor.get_by_email(email))
    if len(users) == 0:
        logging.error(f"Не нашли пользователя {email}, чтобы уведомить о списании с него "
                      f"ресурса {repr(resource)}")
        return None
    if users[0].chat_id is None:
        logging.info(f"Не уведомили {email} о списании ресурса {repr(resource)}: "
                     f"он еще не отправлял сообщений боту")
        return None
    chat_id = users[0].chat_id
    await message.bot.send_message(chat_id, f"С вас списали {resource.short_str()}")


async def notify_user_about_take(message: Message, email: str, resource: Resource) -> None:
    """Уведомляет пользователя, что на него записали ресурс"""
    users: list[Visitor] = (await Visitor.get_by_email(email))
    if len(users) == 0:
        logging.info(f"Из-за ошибки авторизации не удалось уведомить пользователя с почтой {email} "
                     f"о записи на него ресурса {repr(resource)}")
        return None
    if users[0].chat_id is None:
        logging.info(
            f"Не уведомили {email} о записи ресурса {repr(resource)}: пользователь еще не отправлял сообщений боту")
        return None
    chat_id = users[0].chat_id
    await message.bot.send_message(
        chat_id,
        f"На вас записали {resource.short_str()}\r\n/return{resource.id} - если уже неактуально"
    )


async def notify_next_user_about_take(message: Message, next_user_email: str, resource: Resource) -> None:
    """Уведомляет пользователя, что пришла его очередь, и на него записан ресурс"""
    users: list[Visitor] = (await Visitor.get_by_email(next_user_email))
    if len(users) == 0:
        logging.error(f"Не нашли пользователя {next_user_email}, чтобы уведомить "
                      f"о записи на него ресурса: {repr(resource)}")
        return None
    if users[0].chat_id is None:
        logging.error(f"Не уведомили {next_user_email}, что пришла его очередь занять "
                      f"{repr(resource)}: отсутствует chat_id")
        return None
    next_user_chat_id = users[0].chat_id
    await message.bot.send_message(
        next_user_chat_id,
        f"Записали на вас устройство {resource.name} c артикулом {resource.vendor_code}. Нажмите:\r\n"
        f"/update_address{resource.id} - если подтверждаете,\r\n"
        f"/return{resource.id} - если уже неактуально"
    )


async def pass_resource_to_next_user(resource_id: int) -> Optional[str]:
    """Передает ресурс следующему пользователю в очередь, если очередь есть"""
    next_user_email = None
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            stmt = select(Record).where(Record.resource == resource_id).where(Record.action == ActionType.QUEUE)
            result = await session.scalars(stmt)
            queue = result.all()
            if len(queue) != 0:
                record_with_next_user: Record = queue[-1]
                next_user_email = record_with_next_user.user_email
                resource = await Resource.take(resource_id=resource_id, user_email=record_with_next_user.user_email)
                record = await Record.add(resource_id, record_with_next_user.user_email, ActionType.TAKE)
                await session.delete(record_with_next_user)
                logging.info(
                    f"После возврата автоматически записался на пользователя ресурс: {repr(resource)}"
                )
                logging.info(
                    f"При передаче ресурса следующему пользователю {next_user_email} была автоматически удалена "
                    f"запись QUEUE от даты {record_with_next_user.updated_at} "
                    f"и добавлена запись TAKE от даты {record.updated_at}")
                await session.commit()
    return next_user_email


async def get_resource_queue(resource_id: int) -> list[Record]:
    """Возвращает очередь на определенный ресурс - записи с действием QUEUE"""
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            stmt = select(Record).where(Record.resource == resource_id).where(Record.action == ActionType.QUEUE)
            result = await session.scalars(stmt)
            queue = result.all()
    return list(queue)


async def is_user_in_queue(user: Visitor, resource: Resource, records: Optional[list[Record]]) -> bool:
    """Проверяет, есть ли пользователь в очереди на определенный ресурс"""
    if not records:
        records = await Record.get({"user_email": user.email})
    user_in_queue = False
    for record in records:
        if record.user_email == user.email and record.resource == resource.id and record.action == ActionType.QUEUE:
            user_in_queue = True
    return user_in_queue


async def get_available_action(resource: Resource, chat_id: int) -> ActionType:
    """Возвращает для текущего ресурса доступное действие"""
    user = await Visitor.get_current(chat_id)
    records: list[Record] = await Record.get({"user_email": user.email})
    if not resource.user_email:
        return ActionType.TAKE
    elif resource.user_email == user.email:
        return ActionType.RETURN
    elif await is_user_in_queue(user, resource, records):
        return ActionType.LEAVE
    else:
        return ActionType.QUEUE


async def format_note(resource: Resource, chat_id: int) -> str:
    """Выводит информацию про ресурс + доступные действия"""
    command = (await get_available_action(resource, chat_id)).value
    user = await Visitor.get_current(chat_id)
    if user.is_admin:
        return f"{str(resource)}\r\n{command}{resource.id}\r\n{ActionType.EDIT.value}{resource.id}\r\n\r\n"
    else:
        return f"{str(resource)}\r\n{command}{resource.id}\r\n\r\n"


async def format_notes(resources: list[Resource], chat_id: int) -> str:
    """Выводит информацию про ресурсы + доступные действия"""
    return "".join([await format_note(resource, chat_id) for resource in resources])


async def get_keyboard_for_resources(
        page: int,
        resources: list[Resource],
        command_name: str,
        chat_id: int
) -> tuple[str, InlineKeyboardMarkup]:
    """Возвращает стандартную клавиатуру и информацию про ресурсы"""
    paginator = Paginator(page, resources)
    keyboard = paginator.create_keyboard(command_name)
    notes = await format_notes(paginator.get_objects_on_page(), chat_id)
    reply = paginator.result_message() + notes
    return reply, keyboard


def nameof(field: Any) -> str:
    """
    Возвращает название аттрибута класса.
    При написании аттрибута строкой можно ошибиться, например, написать "email".
    Эта ситуация исключена, если писать nameof(Resource.user_email)
    """
    return str(field).split(".")[1]


async def return_resource(resource_id: int) -> None:
    """Списывает ресурс с посетителя и удаляет запись с TAKE"""
    resources = await Resource.get_by_primary(resource_id)
    resource = resources[0]
    await Resource.free(resource_id)
    await Record.delete(**{
        nameof(Record.resource): resource_id,
        nameof(Record.action): ActionType.TAKE,
        nameof(Record.user_email): resource.user_email})


async def delete_all_free_resources() -> None:
    """Удаляет все незанятые пользователями ресурсы"""
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            stmt = select(Resource).filter(Resource.user_email == None)
            result = await session.scalars(stmt)
            resources = result.all()
            for resource in resources:
                await session.delete(resource)
            await session.commit()


async def drop_base() -> None:
    """Удаляет базу :)"""
    async with models.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def init_base() -> None:
    """Создает структуру БД и записывает действия и категории, если их нет"""
    models.init_engine()
    try:
        async with models.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await pre_fill_bd()
        logging.info("БД успешно инициализирована")
    except Exception:
        logging.error("Не удалось инициализировать БД, работа приложения завершена", exc_info=True)
        exit()


async def pre_fill_bd() -> None:
    """Предзаполняет БД заранее известными списками действий и категорий"""
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            stmt = select(Action)
            result = await session.scalars(stmt)
            actions = result.all()
            if len(actions) != 0:
                logging.info("БД не пустая, поэтому не требует предзаполнения")
                return
            for action in ActionType:
                session.add(Action(type=action))
            for category in CATEGORIES:
                session.add(Category(name=category))
            await session.commit()


async def prepare_test_data() -> None:
    """
    Добавляет в чат тестовые данные
    Важно: если указать произвольный chat_id, при отправке сообщения приложение упадет
    """
    test_email = "test@skbkontur.ru"
    my_email = "mnoskov@skbkontur.ru"
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            stmt = select(Visitor)
            result = await session.scalars(stmt)
            users = result.all()
            if len(users) != 0:
                logging.info("Добавление тестовых данных отменено т.к. БД не пустая")
                return
            session.add_all(
                [
                    Visitor(chat_id=230809906, email=my_email, is_admin=True),
                    Visitor(email=test_email),
                ]
            )
            await session.commit()
    await Resource.add(**{"id": 1, "name": "Рыжик", "category_name": "ККТ", "vendor_code": "49494"})
    await Resource.add(**{"id": 2, "name": "Сигма", "category_name": "Сканер", "vendor_code": "222"})
    await Resource.add(**{"id": 3, "name": "Штрих-Слим", "category_name": "Весы", "vendor_code": "2223"})
    await Resource.take(1, my_email, "Дом в лесу", datetime(2024, 6, 30))
    await Record.add(1, my_email, ActionType.TAKE)

    # await Resource.take(2, my_email)
    # await Record.add(2, test_email, ActionType.QUEUE)
    for i in range(30):
        await Resource.add(**{
            "id": i+999,
            "name": f"Вертолет{i + 999}",
            "category_name": "ККТ",
            "vendor_code": f"{i + 999}",
            "user_email": test_email})
    logging.info("В БД добавлены тестовые данные")


async def get_last_alembic_revision() -> Optional[str]:
    """Получает номер ревизии - ее алембик хранит прямо в нашей базе"""
    async_session = async_sessionmaker(models.engine, expire_on_commit=False)
    async with async_session() as session:
        async with session.begin():
            result = await session.scalars(text("select * from alembic_version"))
            revisions = result.all()
            if len(revisions) != 0:
                return str(revisions[0])
            return None


async def get_revisions_as_string_io() -> StringIO:
    """
    Получает историю ревизий командой алембика в консоли
    При ошибке возвращает пустую строку
    """
    shell = await asyncio.create_subprocess_shell(
        cmd="cd .. && alembic history --verbose",
        shell=True,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await shell.communicate()
    revisions = "" if stderr else stdout.decode("utf-8")
    result = StringIO()
    result.name = str("revision")
    result.write(revisions)
    result.seek(0)
    return result


async def add_resource_from_df(df: pd.DataFrame, message: Message):
    for index, row in df.iterrows():
        resource = Resource(
            id=int(row[ResourceColumn.id.value]),
            name=str(row[ResourceColumn.name.value]),
            category_name=str(row[ResourceColumn.category_name.value]),
            vendor_code=str(row[ResourceColumn.vendor_code.value]),
            reg_date=resource_checker.try_convert_to_ddmmyyyy(str(row[ResourceColumn.reg_date.value])) if pd.notna(
                row[ResourceColumn.reg_date.value]) else None,
            firmware=row[ResourceColumn.firmware.value] if pd.notna(row[ResourceColumn.firmware.value]) else None,
            comment=row[ResourceColumn.comment.value] if pd.notna(row[ResourceColumn.comment.value]) else None,
            user_email=row[ResourceColumn.user_email.value] if pd.notna(row[ResourceColumn.user_email.value]) else None,
            address=row[ResourceColumn.address.value] if pd.notna(row[ResourceColumn.address.value]) else None,
            return_date=resource_checker.try_convert_to_ddmmyyyy(
                str(row[ResourceColumn.return_date.value])) if pd.notna(
                row[ResourceColumn.return_date.value]) else None,
        )
        if resource.user_email is not None:
            await Visitor.add_if_needed(resource.user_email)
        await Resource.add_existed(resource)
        user_name = strings.get_username_str(message)
        logging.info(
            f"Пользователь{user_name}с chat_id {message.chat.id} добавил ресурс {repr(resource)}")
