from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from src.database.db import get_db
from src.services.contacts import ContactService
from src.schemas.contacts import ContactSchema, ContactUpdateSchema, ContactResponse
from src.conf import messages

router = APIRouter(prefix="/contacts", tags=["contacts"])


def get_contact_service(db: AsyncSession = Depends(get_db)) -> ContactService:
    """
    Повертає сервіс для роботи з контактами.

    Args:
        db: Асинхронна сесія SQLAlchemy (DI через Depends).

    Returns:
        ContactService: Сервіс із бізнес-логікою над контактами.
    """
    return ContactService(db)


@router.post(
    "/",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    name="Створення контакту",
    description="Створює контакт. Якщо email або телефон вже існують — повертає 409.",
    response_description="Повертає дані створеного контакту.",
)
async def create_contact(
    body: ContactSchema, service: ContactService = Depends(get_contact_service)
):
    """
    Створює новий контакт з перевіркою унікальності.

    - Спочатку перевіряємо, чи існує контакт з таким email або телефоном.
    - Якщо так — 409 CONFLICT.
    - Якщо ні — створюємо запис.

    Плюс додаткова «страховка» від конкуренції: ловимо IntegrityError,
    якщо унікальні індекси БД спрацювали раніше (race condition).
    """
    existing = await service.get_by_email_or_phone(str(body.email), body.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Контакт з email '{body.email}' або телефоном '{body.phone}' вже існує",
        )

    return await service.create_contact(body)


@router.get(
    "/",
    response_model=list[ContactResponse],
    name="Всі контакти",
    description="Вибирає з бази даних всі контакти з пагінацією",
    response_description="Повертає список всіх контактів",
)
async def get_all_contacts(
    limit: int = Query(10, ge=1, le=500),
    offset: int = Query(0, ge=0),
    service: ContactService = Depends(get_contact_service),
):
    """
    Отримує список контактів з пагінацією.

    Args:
        limit: Максимальна кількість записів.
        offset: Зсув від початку вибірки.
        service: Сервіс контактів (DI).

    Returns:
        list[ContactResponse]: Список контактів (може бути порожнім).
    """
    return await service.get_all_contacts(limit, offset)


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    name="Пошук за id",
    description="Шукає контакт за його id",
    response_description="Повертає контакт за його id або 404, якщо не знайдено",
)
async def get_contact_by_id(
    contact_id: int, service: ContactService = Depends(get_contact_service)
):
    """
    Отримує контакт за ідентифікатором.

    Args:
        contact_id: Ідентифікатор контакту.
        service: Сервіс контактів (DI).

    Raises:
        HTTPException(404): Якщо контакт не знайдено.

    Returns:
        ContactResponse: Знайдений контакт.
    """
    contact = await service.get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.contact_not_found,
        )
    return contact


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    name="Оновлення контакту",
    description="Оновлює дані контакту. Перевіряє унікальність email та телефону.",
    response_description="Повертає оновлений контакт або 404, якщо не знайдено.",
)
async def update_contact(
    contact_id: int,
    body: ContactUpdateSchema,
    service: ContactService = Depends(get_contact_service),
):
    """
    Оновлює контакт із перевіркою унікальності email та телефону.

    Args:
        contact_id: Ідентифікатор контакту.
        body: Дані для оновлення (будь-яке поле може бути None).
        service: Сервіс контактів.

    Raises:
        HTTPException(404): Якщо контакт не знайдено.
        HTTPException(409): Якщо email або телефон вже використовуються іншим контактом.

    Returns:
        ContactResponse: Оновлений контакт.
    """
    update_data = body.model_dump(exclude_unset=True)

    # Перевірка унікальності тільки якщо передано email/phone
    email = update_data.get("email")
    phone = update_data.get("phone")

    if email or phone:
        exists_conflict = await service.exists_other_with_email_or_phone(
            contact_id, email, phone
        )
        if exists_conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Інший контакт вже має цей email або телефон",
            )

    contact = await service.update_contact(contact_id, body)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.contact_not_found.get(),
        )
    return contact


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    name="Видалення контакта",
    description="Видаляє контакт за його id",
    response_description="Повертає None або 404, якщо контакту немає",
)
async def delete_contact(
    contact_id: int, service: ContactService = Depends(get_contact_service)
):
    """
    Видаляє контакт за ідентифікатором.

    Args:
        contact_id: Ідентифікатор контакту.
        service: Сервіс контактів (DI).

    Raises:
        HTTPException(404): Якщо контакт не знайдено.

    Returns:
        None
    """
    contact = await service.remove_contact(contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=messages.contact_not_found,
        )
    return None


@router.get(
    "/search/",
    response_model=list[ContactResponse],
    name="Пошук по параметрам",
    description="Пошук контакту за ім'ям, прізвищем або поштою",
    response_description="Повертає список контактів (може бути порожнім)",
)
async def get_contact_by_query(
    query: str = Query(..., min_length=1, max_length=100, example="Оксана"),
    service: ContactService = Depends(get_contact_service),
):
    """
    Повертає список контактів, що відповідають рядку пошуку (ILike).

    Args:
        query: Рядок пошуку (по first_name, last_name, email).
        service: Сервіс контактів (DI).

    Returns:
        list[ContactResponse]: Список відповідних контактів (може бути порожнім).
    """
    return await service.get_contact_by_query(query)


@router.get(
    "/upcoming_birthdays/",
    response_model=list[ContactResponse],
    name="Контакти за ДН",
    description="Список контактів, у яких день народження у найближчі дні від 1 до 30 (обирається користувачем)",
    response_description="Повертає список контактів або повідомлення, якщо список порожній",
)
async def get_contacts_by_upcoming_birthdays(
    days: int = Query(7, ge=1, le=30),
    service: ContactService = Depends(get_contact_service),
):
    """
    Повертає контакти з днями народження в найближчі `days` днів.

    Якщо нічого не знайдено — повертає 200 OK з JSON-об’єктом:
    `{"message": "...", "contacts": []}`.

    Args:
        days: Кількість днів наперед (1–30).
        service: Сервіс контактів (DI).

    Returns:
        list[ContactResponse] | JSONResponse: Список контактів або повідомлення з порожнім списком.
    """
    contacts = await service.get_contacts_by_upcoming_birthdays(days=days)
    if not contacts:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": f"Немає контактів з ДН у найближчі {days} днів",
                "contacts": [],
            },
        )
    return contacts
