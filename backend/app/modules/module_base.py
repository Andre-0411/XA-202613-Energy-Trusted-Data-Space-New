"""Module base utilities."""
from typing import TypeVar, Generic, Type, List, Optional, Any, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from pydantic import BaseModel

from app.schemas import PaginationParams, PaginatedResponse

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseService(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base service with common CRUD operations."""

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_or_404(self, db: Session, id: int, detail: str = "资源不存在") -> ModelType:
        obj = self.get(db, id)
        if obj is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
        return obj

    def get_list(
        self,
        db: Session,
        pagination: PaginationParams,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_desc: bool = False,
    ) -> tuple[List[ModelType], int]:
        query = db.query(self.model)

        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)

        total = query.count()

        if order_by and hasattr(self.model, order_by):
            column = getattr(self.model, order_by)
            query = query.order_by(column.desc() if order_desc else column)
        else:
            query = query.order_by(self.model.id.desc())

        items = query.offset((pagination.page - 1) * pagination.page_size).limit(pagination.page_size).all()
        return items, total

    def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        db_obj = self.model(**obj_in.model_dump())
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, db_obj: ModelType, obj_in: UpdateSchemaType) -> ModelType:
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = self.get_or_404(db, id)
        db.delete(obj)
        db.commit()

    def paginated_response(self, items: List[ModelType], total: int, pagination: PaginationParams, schema_class: Type[BaseModel]) -> PaginatedResponse:
        return PaginatedResponse(
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            items=[schema_class.model_validate(item) for item in items],
        )
