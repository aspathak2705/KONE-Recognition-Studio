import uuid
from typing import Tuple
from pathlib import Path
from fastapi import UploadFile, HTTPException


def save_uploaded_file(file: UploadFile, target_dir: Path, allowed_extensions: set, max_size_mb: int = 20) -> Tuple[Path, str]:
    target_dir.mkdir(parents=True, exist_ok=True)
    
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{file_ext}'. Allowed: {', '.join(sorted(allowed_extensions))}"
        )
    
    # Safe UUID filename to prevent path traversal
    file_id = uuid.uuid4().hex
    safe_filename = f"{file_id}{file_ext}"
    destination = target_dir / safe_filename
    
    file.file.seek(0)
    content = file.file.read()
    
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    max_bytes = max_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed limit of {max_size_mb}MB."
        )
        
    with open(destination, "wb") as f:
        f.write(content)
        
    return destination, file_id
