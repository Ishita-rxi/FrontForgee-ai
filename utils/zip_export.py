import io
import zipfile


def build_zip(files: dict, root_folder: str = "generated-app") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(f"{root_folder}/{path}", content)
    buffer.seek(0)
    return buffer.read()
