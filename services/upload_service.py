import os
import uuid
from werkzeug.utils import secure_filename
import config

def is_allowed_file(filename):
    """Verifies that the uploaded file has a safe and permitted image extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in config.ALLOWED_EXTENSIONS

def save_uploaded_file(file_storage, subfolder="issues"):
    """
    Saves an uploaded file safely to disk and returns its relative filename.
    Architecture is prepared for S3 cloud migration in Sprint 6.
    """
    if not file_storage or not file_storage.filename:
        return None

    if not is_allowed_file(file_storage.filename):
        raise ValueError("Invalid file format. Allowed extensions: PNG, JPG, JPEG, GIF, WEBP.")

    # Sanitize and generate unique collision-free filename
    original_name = secure_filename(file_storage.filename)
    extension = original_name.rsplit(".", 1)[1].lower()
    unique_filename = f"{subfolder}_{uuid.uuid4().hex[:10]}.{extension}"

    target_dir = config.UPLOAD_FOLDER
    os.makedirs(target_dir, exist_ok=True)
    full_path = os.path.join(target_dir, unique_filename)

    file_storage.save(full_path)

    # Replicate to Amazon S3 (if enabled or simulated)
    try:
        from services.aws_service import aws_service
        aws_service.upload_file_to_s3(full_path, unique_filename)
    except Exception as e:
        # Fallback to local storage only if S3 sync encounters error
        pass

    return unique_filename
