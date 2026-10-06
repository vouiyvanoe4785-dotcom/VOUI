import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils.http import content_disposition_header


def serve_file(field_file, filename, as_attachment=False):
    """Send an uploaded file after the calling view has checked access.

    Uploaded files are never exposed under a public URL. When
    PROTECTED_MEDIA_ACCEL_PREFIX is set (e.g. "/protected-media/"), the transfer is handed
    to Nginx with X-Accel-Redirect to an `internal` location; otherwise Django streams it.
    """
    if not field_file:
        raise Http404("Aucun fichier.")
    prefix = settings.PROTECTED_MEDIA_ACCEL_PREFIX
    if prefix:
        response = HttpResponse()
        response["X-Accel-Redirect"] = prefix.rstrip("/") + "/" + field_file.name.lstrip("/")
        response["Content-Type"] = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        response["Content-Disposition"] = content_disposition_header(as_attachment, filename)
        return response
    try:
        handle = field_file.open("rb")
    except FileNotFoundError:
        raise Http404("Fichier introuvable.")
    return FileResponse(handle, as_attachment=as_attachment, filename=filename)
