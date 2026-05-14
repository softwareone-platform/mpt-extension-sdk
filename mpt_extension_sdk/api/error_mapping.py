from typing import Any

from pydantic import ValidationError as PydanticValidationError

from mpt_extension_sdk.api.models.errors import ErrorDetail


class PydanticValidationErrorMapper:
    """Map Pydantic validation errors to SDK problem-details field errors."""

    @classmethod
    def map(cls, error: PydanticValidationError) -> list[ErrorDetail]:
        """Map Pydantic validation details to the SDK problem-details shape."""
        return [
            ErrorDetail(
                pointer=cls.map_pointer(validation_error.get("loc", ())),
                detail=validation_error.get("msg", "Invalid value"),
            )
            for validation_error in error.errors()
        ]

    @classmethod
    def map_pointer(cls, location: tuple[Any, ...]) -> str:
        """Translate a Pydantic error location to a JSON-pointer-like path."""
        cleaned_location = [
            str(location_part) for location_part in location if location_part != "body"
        ]
        if cleaned_location:
            sub_loc = "/".join(cleaned_location)
            return f"#/{sub_loc}"
        return "#"
