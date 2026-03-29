from app.services.multimodal_service import MultimodalService


class ImageProcessingService:
    def __init__(self, multimodal_service: MultimodalService | None = None) -> None:
        self.multimodal_service = multimodal_service or MultimodalService()

    def extract_ocr_text(self, image_path: str) -> str:
        return ""

    def process_image(self, image_path: str) -> dict[str, str]:
        return {
            "ocr_text": self.extract_ocr_text(image_path),
            "image_description": self.multimodal_service.describe_image(image_path),
        }
