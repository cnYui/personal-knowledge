from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.memory import Memory, MemoryImage
from app.schemas.upload import MemoryUploadResponse
from app.services.image_processing_service import ImageProcessingService
from app.utils.file_storage import save_upload

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
image_processing_service = ImageProcessingService()


@router.post("/memories", response_model=MemoryUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_memory(
    title: str = Form(''),
    content: str = Form(...),
    group_id: str = Form('default'),
    images: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
):
    resolved_title = title.strip() or '标题生成中'
    title_status = 'pending' if resolved_title == '标题生成中' else 'ready'
    memory = Memory(
        title=resolved_title,
        title_status=title_status,
        content=content,
        group_id=group_id.strip() or 'default',
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)

    processed_count = 0
    for image in images:
        data = await image.read()
        stored_path = save_upload(settings.upload_dir, image.filename or "image.bin", data)
        processed = image_processing_service.process_image(stored_path)
        db.add(
            MemoryImage(
                memory_id=memory.id,
                original_file_name=image.filename or "image.bin",
                stored_path=stored_path,
                ocr_text=processed["ocr_text"],
                image_description=processed["image_description"],
            )
        )
        processed_count += 1

    db.commit()

    return MemoryUploadResponse(
        id=memory.id,
        title=memory.title,
        title_status=title_status,
        content=memory.content,
        group_id=memory.group_id,
        images_count=processed_count,
        processing_status='pending' if title_status == 'pending' else 'completed',
    )
