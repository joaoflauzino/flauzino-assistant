from pydantic import BaseModel


class GraphImageResponse(BaseModel):
    """Response containing a base64-encoded graph image."""

    image_base64: str
