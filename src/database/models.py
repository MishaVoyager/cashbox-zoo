"""
Модуль с описанием моделей, а также вспомогательными методами для получения данных

Classes
--------
Base
    Класс, от которого наследуются остальные модели.
    Содержит метадату, которая необходима для генерации миграций.
    Также реализует универсальные вспомогательные методы: get_all, get_by_primary и т.д.
    Вызывать их можно для конкретного класса, например: Resource.get_all, Record.get_all
ActionType(Enum)
    Тип действия над ресурсом
Action
    Модель на основе енама ActionType
Record
    Модель записи ресурса на пользователя. Больше всего нужна для очередей.
Visitor
    Модель пользователя, "посетителя" библиотеки
Category
    Категория ресурсов. В случае нашего бота список категорий известен заранее
Resource
    Основная модель, которая описывает единицу нашей библиотеки
"""

import inspect
import logging
from datetime import datetime, timedelta
from enum import StrEnum
from io import StringIO
from typing import Any, Optional, Self

import sqlalchemy
from aiogram.types import Message
from sqlalchemy import ForeignKey, MetaData, or_, select
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from sqlalchemy.sql.operators import ilike_op

from configs.config import PostgresSettings, Settings

engine: Optional[AsyncEngine] = None

CATEGORIES = ["ККТ", "Весы", "Принтер кухонный", "Планшет", "Терминал", "Сканер", "Другое"]


class Base(AsyncAttrs, DeclarativeBase):
    """Основной класс, от которого наследуются остальные модели"""
    metadata = MetaData(
        naming_convention={
            "ix": "%(column_0_label)s_idx",
            "uq": "%(table_name)s_%(column_0_name)s_key",
            "ck": "%(table_name)s_%(constraint_name)s_check",
            "fk": "%(table_name)s_%(column_0_name)s_%(referred_table_name)s_fkey",
            "pk": "%(table_name)s_pkey"
        }
    )

    @classmethod
    async def add_existed(cls, model: Self) -> Self:
        """Получает готовый объект и добавляет его в БД"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                model = await session.merge(model)
                session.add(model)
                await session.commit()
                return model

    @classmethod
    async def delete_existed(cls, model: Self) -> None:
        """Получает готовый объект и удаляет его из БД"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                model = await session.merge(model)
                await session.delete(model)
                await session.commit()

    @classmethod
    async def get_all(cls, limit: int = 100) -> list[Self]:
        """Получает все объекты с ограничением limit"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).limit(limit)
                result = await session.scalars(stmt)
                objects = result.all()
                return list(objects)

    @classmethod
    async def get(cls, name_and_value: dict[str, Any], limit: int = 100) -> list[Self]:
        """Возвращает список объектов с определенным значением определенного поля"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).filter_by(**name_and_value).limit(limit)
                result = await session.scalars(stmt)
                objects = result.all()
                return list(objects)

    @classmethod
    async def get_by_primary(cls, value: Any) -> list[Self]:
        """Возвращает список объектов с определенным значением поля с primary_key"""
        primary_field_name = ""
        members = inspect.getmembers(cls)
        for name, member in members:
            if hasattr(member, "primary_key") and getattr(member, "primary_key"):
                primary_field_name = name
        if primary_field_name == "":
            raise ValueError(f"Не найден primary key для класса {cls}")
        return await cls.get({primary_field_name: value})

    @classmethod
    async def delete_all(cls, limit: int = 10000) -> None:
        """Удаляет все объекты с определенным лимитом"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                objects = await cls.get_all(limit)
                for obj in objects:
                    await session.delete(obj)
                await session.commit()

    @classmethod
    def get_fields_names(cls) -> list[str]:
        """Возвращает названия полей класса = колонок таблицы"""
        return cls.__table__.columns.keys()

    @classmethod
    def get_fields(cls) -> dict[str, Optional[str]]:
        """Создает словарь, где каждому полю класса присвоен None"""
        return {field: None for field in cls.get_fields_names()}

    @classmethod
    async def get_as_string_io(cls, limit: int = 100) -> StringIO:
        """
        Возвращает StringIO с расширенным выводом про ресурсы (с updated_at) и названием файла
        По умолчанию не выводим updated в repr, поскольку он быстро теряет актуальность
        Алхимия роняет приложение при взаимодействии с неактуальным объектом
        """
        objects = await cls.get_all(limit)
        text = StringIO()
        text.name = str(cls.__tablename__)
        for obj in objects:
            text.write(f"{repr(obj)[:-1]}, updated_at:{getattr(obj, 'updated_at')})\r\n\r\n")
        text.seek(0)
        return text

    @classmethod
    def _prepare_filters_for_strings(cls, fields: list[str], search_key: str) -> list:
        """Готовит фильтры для поиска по тексту"""
        search_filter = list()
        for field in fields:
            atr = getattr(cls, field)
            search_filter.append(ilike_op(atr, f"%{search_key}%"))
            search_filter.append(ilike_op(atr, f"%{search_key.capitalize()}%"))
            search_filter.append(ilike_op(atr, f"%{search_key.upper()}%"))
        return search_filter


class ActionType(StrEnum):
    """Енам со спиской действий над ресурсами"""
    TAKE = "Взять: /take",
    QUEUE = "Встать в очередь: /queue",
    RETURN = "Вернуть: /return",
    LEAVE = "Покинуть очередь: /leave"
    EDIT = "Отредактировать: /edit"


class Action(Base):
    """Модель таблицы со списком действий над ресурсами"""
    __tablename__ = "action"

    type: Mapped[ActionType] = mapped_column(primary_key=True, unique=True)

    def __repr__(self) -> str:
        return f"Action(type={self.type})"

    def __str__(self) -> str:
        return f"Действие {self.type})"


class Record(Base):
    """Модель записи ресурса на пользователя"""
    __tablename__ = "record"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource: Mapped[int] = mapped_column(ForeignKey("resource.id", onupdate="cascade", ondelete="cascade"))
    user_email: Mapped[str] = mapped_column(ForeignKey("visitor.email", onupdate="cascade", ondelete="cascade"))
    action: Mapped[Action] = mapped_column(ForeignKey("action.type", onupdate="cascade", ondelete="cascade"))
    created_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"Record(id={self.id}, " \
               f"resource={self.resource}, " \
               f"user_email={self.user_email}, " \
               f"action={self.action}, " \
               f"created_at={self.created_at})"

    def __str__(self) -> str:
        return f"Запись с id {self.id}: " \
               f"пользователь с почтой {self.user_email} " \
               f"выполнил действие {self.action} " \
               f"над ресурсом {self.resource}"

    @classmethod
    async def delete(cls, **fields) -> bool:
        """Удаляет записи с определенными значениями определенных полей"""
        for field in fields.keys():
            if field not in cls.get_fields_names():
                logging.error(f"В метод Record.delete некорректно передано поле field: {field}")
                return False
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                records = await cls.get(fields)
                if len(records) == 0:
                    return False
                await session.delete(records[-1])
                await session.commit()
        return True

    @classmethod
    async def add(cls, resource_id: int, email: str, action: ActionType) -> "Record":
        """Добавляет новую запись"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                record = Record(**{"resource": resource_id, "user_email": email, "action": action})
                session.add(record)
                await session.commit()
                return record


class Visitor(Base):
    """Модель 'посетителя' библиотеки ресурсов"""
    __tablename__ = "visitor"

    id: Mapped[int] = mapped_column(sqlalchemy.Identity(start=1, increment=1))
    email: Mapped[str] = mapped_column(primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    chat_id: Mapped[Optional[int]] = mapped_column()
    user_id: Mapped[Optional[int]] = mapped_column()
    full_name: Mapped[Optional[str]] = mapped_column()
    username: Mapped[Optional[str]] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()
    created_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now(), onupdate=func.now())
    resources = relationship("Resource")
    records = relationship("Record")

    def __repr__(self) -> str:
        return f"Visitor(id={self.id}, " \
               f"name={self.email}, " \
               f"chat_id={self.chat_id or 'None'}, " \
               f"is_admin={self.is_admin}, " \
               f"user_id={self.user_id or 'None'}, " \
               f"full_name={self.full_name or 'None'}, " \
               f"username={self.username or 'None'}, " \
               f"comment={self.comment or 'None'}, " \
               f"created_at={self.created_at or 'None'})"

    def __str__(self) -> str:
        return ("".join(
            [
                f"{self.id}\r\n",
                f"Почта: {self.email}\r\n",
                f"Chat_id: {self.chat_id or 'None'}\r\n",
                f"Уровень прав: {'админ' if self.is_admin else 'пользователь'}\r\n",
                f"Полное имя: {self.full_name}\r\n" if self.full_name is not None else "",
                f"Ник: {self.username}\r\n" if self.username is not None else "",
                f"Коммент: {self.comment}\r\n" if self.comment is not None else "",
            ]))[:-2]

    @classmethod
    async def get_by_email(cls, email: str) -> "list[Visitor]":
        """Находит пользователей по email"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).where(cls.email == email)
                result = await session.scalars(stmt)
                objects = result.all()
                return list(objects)

    @classmethod
    async def search(cls, search_key: str, limit: int = 100) -> "list[Visitor]":
        """Находит пользователей по поисковой фразе"""
        filters = list()
        if search_key.isnumeric():
            filters.append(Visitor.id.in_([int(search_key)]))
            filters.append(Visitor.chat_id.in_([int(search_key)]))
            filters.append(Visitor.user_id.in_([int(search_key)]))
        else:
            filters = cls._prepare_filters_for_strings(
                fields=["email", "full_name", "username", "comment"],
                search_key=search_key
            )
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).filter(or_(*filters)).limit(limit)
                result = await session.scalars(stmt)
                resources = result.all()
                return list(resources)

    @classmethod
    async def auth(cls, email: str, message: Message) -> "Visitor":
        """
        Создает нового пользователя или обновляет поля существующего
        при первом обращении к боту
        """
        is_admin = email in Settings().admins.split()
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).where(cls.email == email)
                result = await session.scalars(stmt)
                users_with_email = result.all()
                if len(users_with_email) != 0:
                    users_with_email[0].chat_id = message.chat.id
                    logging.info(f"Пользователь изменил chat_id: {repr(users_with_email[0])}")
                    await session.commit()
                    return users_with_email[0]
                else:
                    user = Visitor(
                        email=email,
                        chat_id=message.chat.id,
                        is_admin=is_admin,
                        user_id=message.from_user.id,
                        full_name=message.from_user.full_name,
                        username=message.from_user.username)
                    session.add(user)
                    logging.info(f"Пользователь авторизовался: {repr(user)}")
                    await session.commit()
                    return user

    @classmethod
    async def update_email(cls, visitor_id: int, new_email: str) -> "Optional[Visitor]":
        """Обновляет email пользователя и возвращает пользователя"""
        visitors = await cls.get({"id": visitor_id})
        if len(visitors) == 0:
            return None
        visitor = visitors[0]
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                visitor = await session.merge(visitor)
                visitor.email = new_email
                await session.commit()
                return visitor

    @classmethod
    async def update_comment(cls, visitor_id: int, comment: str) -> "Optional[Visitor]":
        """Обновляет комментарий пользователя и возвращает пользователя"""
        visitors = await Visitor.get({"id": visitor_id})
        if len(visitors) == 0:
            return None
        visitor = visitors[0]
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                visitor = await session.merge(visitor)
                visitor.comment = comment
                await session.commit()
                return visitor

    @classmethod
    async def get_current(cls, chat_id: int) -> "Optional[Visitor]":
        """Находит пользователя по chat_id"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).filter_by(chat_id=chat_id)
                result = await session.scalars(stmt)
                users = result.all()
                if len(users) != 0:
                    return users[0]
        logging.error(f"Не найден пользователь с chat_id: {chat_id}")
        return None

    @classmethod
    async def is_exist(cls, chat_id: int) -> bool:
        """Проверяет, что есть строго 1 пользователь с этим chat_id"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).where(cls.chat_id == chat_id)
                result = await session.scalars(stmt)
                users = result.all()
        return len(users) == 1

    @classmethod
    async def add_if_needed(cls, email: str) -> bool:
        """
        Добавляет пользователя с минимальным количеством инфы (email)
        Полезно, когда мы записываем ресурс на пользователя, который еще не
        писал нашему боту - т.е. мы не знаем его chat_id и пока не авторизуем
        """
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).where(cls.email == email)
                result = await session.scalars(stmt)
                users = result.all()
                if len(users) > 0:
                    return False
                session.add(Visitor(email=email))
                await session.commit()
                return True


class Category(Base):
    """Модель категории ресурса"""
    __tablename__ = "category"

    name: Mapped[str] = mapped_column(primary_key=True, unique=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"Category(" \
               f"name={self.name} " \
               f"created_at={self.created_at}" \
               f")"

    def __str__(self) -> str:
        return f"Категория {self.name}"

    @classmethod
    async def add(cls, category_name: str) -> None:
        """Добавляет категорию с определенным именем"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(Category).where(Category.name == category_name)
                result = await session.scalars(stmt)
                categories = result.all()
                if len(categories) == 0:
                    session.add(Category(name=category_name))
                await session.commit()


class Resource(Base):
    """Модель ресурса - в нашем случае устройства"""
    __tablename__ = "resource"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    category_name: Mapped[str] = mapped_column(ForeignKey("category.name"))
    vendor_code: Mapped[str] = mapped_column(unique=True)
    reg_date: Mapped[Optional[datetime]] = mapped_column()
    firmware: Mapped[Optional[str]] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()
    user_email: Mapped[Optional[str]] = mapped_column(
        ForeignKey("visitor.email", onupdate="cascade", ondelete="cascade"))
    address: Mapped[Optional[str]] = mapped_column()
    return_date: Mapped[Optional[datetime]] = mapped_column()
    created_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"Resource(id={self.id}, " \
               f"name={self.name}, " \
               f"category_name={self.category_name}, " \
               f"vendor_code={self.vendor_code}, " \
               f"reg_date={self.reg_date or 'None'}, " \
               f"firmware={self.firmware or 'None'}, " \
               f"comment={self.comment or 'None'}, " \
               f"user_email={self.user_email or 'None'}, " \
               f"address={self.address or 'None'}, " \
               f"return_date={self.return_date or 'None'}, " \
               f"created_at={self.created_at or 'None'}" \
               f")"

    def __str__(self) -> str:
        return ("".join(
            [
                f"{self.id}\r\n",
                f"{self.name} ({self.category_name.lower()})\r\n",
                f"Артикул (ЗН или СН): {self.vendor_code}\r\n",
                f"Зарегистрирован {self.reg_date.strftime(r'%d.%m.%Y')}\r\n" if self.reg_date is not None else "",
                f"Комментарий: {self.comment}\r\n" if self.comment is not None else "",
                f"Прошивка: {self.firmware}\r\n" if self.firmware is not None else "",
                f"Сейчас у пользователя: {self.user_email}\r\n" if self.user_email is not None else "",
                f"Освободится примерно: {self.return_date.strftime(r'%d.%m.%Y')}\r\n" if self.return_date is not None else "",
                f"Где находится: {self.address}\r\n" if self.address is not None else "",
            ]))[:-2]

    def short_str(self) -> str:
        return f"устройство {self.name} с id {self.id} и артикулом {self.vendor_code}"

    @classmethod
    async def get_single(cls, resource_id: int) -> "Optional[Resource]":
        """
        Возвращает строго один ресурс с определенным id
        Полезно, когда мы уверены, что ресурс есть
        """
        resources = await Resource.get_by_primary(resource_id)
        if len(resources) == 0:
            logging.error(f"Не найден ресурс с resource_id={resource_id}")
            return None
        return resources[0]

    @classmethod
    async def get_expiring(cls, soon_expire_days: int = 0) -> "list[Resource]":
        """Возвращает ресурсы, у которых дата возврата >= текущей"""
        notify_until_date = datetime.now() + timedelta(days=soon_expire_days)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).filter(cls.return_date <= notify_until_date)
                result = await session.scalars(stmt)
                resources = result.all()
                return list(resources)

    @classmethod
    async def update(cls, resource_id: int, **fields) -> "Optional[Resource]":
        """
        Обновляет для ресурса определенные значения определенных полей
        Не проверяет валидность полей! Это ответственность resource_checker
        """
        for field in fields.keys():
            if field not in Resource.get_fields_names():
                logging.error(f"В метод Resource.update некорректно передано поле field: {field}")
                return None
        if "user_email" in fields.keys() and fields["user_email"] is not None:
            await Visitor.add_if_needed(email=fields["user_email"])
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        resources = await Resource.get_by_primary(resource_id)
        resource = resources[0]
        async with async_session() as session:
            async with session.begin():
                resource = await session.merge(resource)
                for field, value in fields.items():
                    setattr(resource, field, value)
                await session.commit()
        return resource

    @classmethod
    async def add(cls, **fields) -> "Optional[Resource]":
        """
        Добавляет ресурс с определенными значениями определенных полей
        Не проверяет валидность полей! Это ответственность resource_checker
        """
        for field in fields.keys():
            if field not in Resource.get_fields_names():
                logging.error(f"В метод Resource.update некорректно передано поле field: {field}")
                return None
        if "name" not in fields.keys() or "category_name" not in fields.keys() or "vendor_code" not in fields.keys() or "id" not in fields.keys():
            logging.error(f"При добавлении ресурса в метод не переданы name, category_name, "
                          f"vendor_code или id. Значение fields: {fields}")
            return None
        if "user_email" in fields.keys() and fields["user_email"] is not None:
            await Visitor.add_if_needed(email=fields["user_email"])
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                resource = Resource(**fields)
                session.add(resource)
                await session.commit()
                return resource

    @classmethod
    async def take(cls, resource_id: int, user_email: str, address: Optional[str] = None,
                   return_date: Optional[datetime] = None) -> "Optional[Resource]":
        """Записывает ресурс на пользователя"""
        resources = await cls.get({"id": resource_id})
        if len(resources) == 0:
            logging.error(f"Не найден ресурс с resource_id {resource_id}, "
                          f"пользователь {user_email} будет расстроен")
            return None
        resource = resources[0]
        await Visitor.add_if_needed(email=user_email)
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                resource = await session.merge(resource)
                resource.user_email = user_email
                resource.address = address
                resource.return_date = return_date
                await session.commit()
                return resource

    @classmethod
    async def free(cls, resource_id: int) -> "Resource":
        """Списывает ресурс с пользователя"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).where(cls.id == resource_id)
                result = await session.scalars(stmt)
                resources = result.all()
                resource = resources[0]
                resource.user_email = None
                resource.address = None
                resource.return_date = None
                await session.commit()
                return resource

    @classmethod
    async def search(cls, search_key: str, limit: int = 100, max_id: int = 1000000) -> "list[Resource]":
        """
        Ищет ресурсы по запросу search_key: если это число меньше max_id - по id,
        иначе - по другим полям
        """
        if search_key.isnumeric() and int(search_key) < max_id:
            filters = [Resource.id.in_([int(search_key)])]
        else:
            filters = cls._prepare_filters_for_strings(
                fields=["name", "category_name", "user_email", "vendor_code"],
                search_key=search_key
            )
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).filter(or_(*filters)).limit(limit)
                result = await session.scalars(stmt)
                resources = result.all()
                return list(resources)

    @classmethod
    async def delete(cls, resource_id: int) -> None:
        """Удаляет ресурс"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                resource = await cls.get_single(resource_id)
                await session.delete(resource)
                await session.commit()

    @classmethod
    async def get_resources_on_user(cls, user: "Visitor") -> "list[Resource]":
        """Возвращает список ресурсов, записанных на пользователя"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).where(cls.user_email == user.email)
                result = await session.scalars(stmt)
                resources = result.all()
                return list(resources)

    @classmethod
    async def get_by_vendor_code(cls, vendor_code: str) -> "list[Resource]":
        """Ищет ресурс по значению vendor_code"""
        return await Resource.get({"vendor_code": vendor_code})

    @classmethod
    async def get_categories(cls) -> "list[str]":
        """Возвращает активные категории - к которым относится минимум 1 ресурс"""
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        async with async_session() as session:
            async with session.begin():
                stmt = select(cls).with_only_columns(cls.category_name).distinct()
                result = await session.scalars(stmt)
                categories = result.all()
                return list(categories)

    async def get_csv_value(self) -> list[str]:
        """Формирует список полей ресурса для csv файла с выгрузкой"""
        return [
            str(self.id),
            self.name,
            self.category_name,
            self.vendor_code,
            self.reg_date.strftime(r'%d.%m.%Y') if self.reg_date is not None else " ",
            self.firmware if self.firmware is not None else " ",
            self.comment if self.comment is not None else " ",
            self.user_email if self.user_email is not None else " ",
            self.address if self.address is not None else " ",
            self.return_date.strftime(r'%d.%m.%Y') if self.return_date is not None else " "
        ]


def init_engine() -> None:
    """Запускает engine и присваивает значение глобальной переменной"""
    global engine
    engine = create_async_engine(PostgresSettings().get_connection_str())
