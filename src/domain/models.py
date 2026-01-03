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

from datetime import datetime
from enum import StrEnum
from io import StringIO
from typing import Optional, Any

import sqlalchemy
from sqlalchemy import ForeignKey, MetaData, BigInteger
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func, expression

from configs.config import Settings

CATEGORIES = Settings().get_categories()


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
    def get_fields_names(cls) -> list[str]:
        """Возвращает названия полей класса = колонок таблицы"""
        return cls.__table__.columns.keys()

    @classmethod
    def get_fields(cls) -> dict[str, Optional[str]]:
        """Создает словарь, где каждому полю класса присвоен None"""
        return {field: None for field in cls.get_fields_names()}

    @classmethod
    def get_as_string_io(cls, objects: Any) -> StringIO:
        """
        Возвращает StringIO с расширенным выводом про ресурсы (с updated_at) и названием файла
        По умолчанию не выводим updated в repr, поскольку он быстро теряет актуальность.
        Алхимия роняет приложение при взаимодействии с неактуальным объектом
        """
        text = StringIO()
        text.name = str(cls.__tablename__)
        for obj in objects:
            text.write(f"{repr(obj)[:-1]}, updated_at:{getattr(obj, 'updated_at')})\r\n\r\n")
        text.seek(0)
        return text


class ActionType(StrEnum):
    """Енам со спиской действий над ресурсами"""
    TAKE = "Взять: /take",
    QUEUE = "Встать в очередь: /queue",
    RETURN = "Вернуть: /return",
    LEAVE = "Покинуть очередь: /leave"
    EDIT = "Отредактировать: /edit"
    CHANGE = "Изменить дату: /change"
    HISTORY = "История: /history"


class Record(Base):
    """Модель записи ресурса на пользователя"""
    __tablename__ = "record"

    id: Mapped[int] = mapped_column(primary_key=True)
    resource_id: Mapped[int] = mapped_column(ForeignKey("resource.id", onupdate="cascade", ondelete="cascade"))
    user_email: Mapped[str] = mapped_column(ForeignKey("visitor.email", onupdate="cascade", ondelete="cascade"))
    address: Mapped[Optional[str]] = mapped_column()
    enqueue_date: Mapped[Optional[datetime]] = mapped_column()
    take_date: Mapped[Optional[datetime]] = mapped_column()
    return_date: Mapped[Optional[datetime]] = mapped_column()
    finished: Mapped[bool] = mapped_column(server_default=expression.false())
    resource = relationship("Resource", back_populates="records", lazy="joined", uselist=False)
    visitor = relationship("Visitor", back_populates="records", lazy="joined", uselist=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now(), onupdate=func.now())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Record):
            return False
        return other.id == self.id

    def __gt__(self, other: 'Record') -> bool:
        if self.take_date is None:
            return False
        if other.take_date is None:
            return True
        return self.enqueue_date > other.enqueue_date

    def __repr__(self) -> str:
        return f"Record(id={self.id}, " \
               f"resource={self.resource}, " \
               f"user_email={self.user_email}, " \
               f"enqueue_date={self.enqueue_date}, " \
               f"take_date={self.enqueue_date}, " \
               f"return_date={self.enqueue_date}, " \
               f"finished={self.finished}, " \
               f"created_at={self.created_at})"

    def __str__(self) -> str:
        return f"Запись с id {self.id}: " \
               f"пользователь с почтой {self.user_email} " \
               f"че-то сделал " \
               f"с ресурсом {self.resource}"


class Visitor(Base):
    """Модель 'посетителя' библиотеки ресурсов"""
    __tablename__ = "visitor"

    id: Mapped[int] = mapped_column(sqlalchemy.Identity(start=1, increment=1))
    email: Mapped[str] = mapped_column(primary_key=True)
    is_admin: Mapped[bool] = mapped_column(default=False)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    user_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    full_name: Mapped[Optional[str]] = mapped_column()
    username: Mapped[Optional[str]] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()
    created_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(server_default=func.now(), onupdate=func.now())
    records = relationship(
        "Record",
        back_populates="visitor",
        lazy="selectin",
    )
    take_records = relationship(
        "Record",
        lazy="selectin",
        primaryjoin="and_(Visitor.email == Record.user_email, Record.take_date != None, Record.finished == False)",
        order_by="Record.take_date.asc()",
        overlaps="records, queue_records, finished_records",
        viewonly=True
    )
    queue_records = relationship(
        "Record",
        lazy="selectin",
        primaryjoin="and_(Visitor.email == Record.user_email, Record.enqueue_date != None, Record.finished == False)",
        order_by="Record.enqueue_date.asc()",
        overlaps="records, take_records, finished_records",
        viewonly=True
    )
    finished_records = relationship(
        "Record",
        uselist=True,
        lazy="selectin",
        primaryjoin="and_(Visitor.email == Record.user_email, Record.finished == True)",
        order_by="Record.return_date.desc()",
        overlaps="records, take_records, queue_records",
        viewonly=True
    )

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
    records = relationship(
        "Record",
        uselist=True,
        lazy="selectin",
        primaryjoin="and_(Resource.id == Record.resource_id, Record.finished == False)",
        back_populates="resource"
    )
    queue_records = relationship(
        "Record",
        lazy="selectin",
        primaryjoin="and_(Resource.id == Record.resource_id, Record.enqueue_date != None, Record.finished == False)",
        order_by="Record.enqueue_date.asc()",
        uselist=True,
        overlaps="finished_records, take_record, records",
        viewonly=True
    )
    take_record = relationship(
        "Record",
        lazy="selectin",
        primaryjoin="and_(Resource.id == Record.resource_id, Record.take_date != None, Record.finished == False)",
        uselist=False,
        overlaps="finished_records, queue_records, records",
        viewonly=True
    )
    finished_records = relationship(
        "Record",
        uselist=True,
        lazy="selectin",
        primaryjoin="and_(Resource.id == Record.resource_id, Record.finished == True)",
        order_by="Record.return_date.desc()",
        overlaps="take_record, queue_records, records",
        viewonly=True
    )
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
            ]))[:-2]

    def short_str(self) -> str:
        return f"{self.name} с id {self.id} и артикулом {self.vendor_code}"
