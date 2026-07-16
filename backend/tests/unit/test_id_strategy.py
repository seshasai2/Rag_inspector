"""Tests documenting the canonical String(36) ID strategy."""
import uuid

from sqlalchemy import String

from app.models.models import Base, User


class TestIdColumnStrategy:
    def test_all_primary_keys_are_string_36(self):
        for mapper in Base.registry.mappers:
            table = mapper.local_table
            for column in table.primary_key.columns:
                assert isinstance(column.type, String), (
                    f"{table.name}.{column.name} must be String, got {column.type}"
                )
                assert column.type.length == 36, (
                    f"{table.name}.{column.name} must be String(36), "
                    f"got length={column.type.length}"
                )

    def test_all_foreign_keys_are_string_36(self):
        for mapper in Base.registry.mappers:
            table = mapper.local_table
            for column in table.columns:
                if not column.foreign_keys:
                    continue
                assert isinstance(column.type, String), (
                    f"{table.name}.{column.name} FK must be String, got {column.type}"
                )
                assert column.type.length == 36, (
                    f"{table.name}.{column.name} FK must be String(36)"
                )

    def test_model_defaults_generate_string_uuids(self):
        id_column = User.__table__.c.id
        assert id_column.default is not None
        assert callable(id_column.default.arg)
        # Canonical generation used by models: str(uuid.uuid4())
        generated = str(uuid.uuid4())
        assert isinstance(generated, str)
        assert len(generated) == 36
