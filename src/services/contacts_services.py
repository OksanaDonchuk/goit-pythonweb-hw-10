from typing import Sequence
from sqlalchemy.ext.asyncio import AsyncSession

from src.entity.models import Contact
from src.repositories.contacts_repository import ContactRepository
from src.schemas.contacts_schema import ContactSchema, ContactUpdateSchema


class ContactService:
    def __init__(self, db: AsyncSession):
        self.contact_repository = ContactRepository(db)

    async def create_contact(self, body: ContactSchema) -> Contact:
        return await self.contact_repository.create_contact(body)

    async def get_all_contacts(self, limit: int, offset: int) -> Sequence[Contact]:
        return await self.contact_repository.get_all_contacts(limit, offset)

    async def get_contact_by_id(self, contact_id: int) -> Contact | None:
        return await self.contact_repository.get_contact_by_id(contact_id)

    async def remove_contact(self, contact_id: int) -> Contact | None:
        return await self.contact_repository.remove_contact(contact_id)

    async def update_contact(
        self, contact_id: int, body: ContactUpdateSchema
    ) -> Contact | None:
        return await self.contact_repository.update_contact(contact_id, body)

    async def get_contact_by_query(self, query: str) -> Sequence[Contact]:
        return await self.contact_repository.get_contact_by_query(query)

    async def get_contacts_by_upcoming_birthdays(
        self, days: int = 7
    ) -> Sequence[Contact]:
        return await self.contact_repository.get_contacts_by_upcoming_birthdays(
            days=days
        )

    async def get_by_email_or_phone(self, email: str, phone: str) -> Contact | None:
        return await self.contact_repository.get_by_email_or_phone(email, phone)

    async def exists_other_with_email_or_phone(
        self, contact_id: int, email: str | None, phone: str | None
    ) -> bool:
        return await self.contact_repository.exists_other_with_email_or_phone(
            contact_id, email, phone
        )
