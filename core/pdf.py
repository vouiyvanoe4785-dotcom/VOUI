import os
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from xhtml2pdf.config.resources import ResourceAccessPolicy


def _link_callback(uri, rel):
    """Map /media/ and /static/ URLs to local files so xhtml2pdf can embed them."""
    media_url, static_url = "/" + settings.MEDIA_URL.lstrip("/"), "/" + settings.STATIC_URL.lstrip("/")
    if uri.startswith(media_url):
        path = os.path.join(settings.MEDIA_ROOT, uri[len(media_url):])
    elif uri.startswith(static_url):
        path = finders.find(uri[len(static_url):]) or ""
    else:
        return uri
    return path if path and os.path.isfile(path) else ""


def _resource_policy():
    """Only local media/static files may be embedded: no network, nothing else on disk.

    xhtml2pdf otherwise confines reads to the process working directory, which would
    silently drop the logo whenever MEDIA_ROOT lives elsewhere (or gunicorn runs from
    another directory).
    """
    roots = [settings.STATIC_ROOT, *settings.STATICFILES_DIRS]
    return ResourceAccessPolicy(
        allow_remote=False,
        base_dir=Path(settings.MEDIA_ROOT),
        extra_roots=tuple(Path(r) for r in roots if r),
    )


def render_pdf(template_name, context):
    html = render_to_string(template_name, context)
    out = BytesIO()
    result = pisa.CreatePDF(
        html, dest=out, encoding="utf-8",
        link_callback=_link_callback, resource_policy=_resource_policy(),
    )
    if result.err:
        raise RuntimeError(f"Échec de la génération du PDF ({result.err} erreur(s)).")
    return out.getvalue()


def pdf_response(template_name, context, filename, download=False):
    response = HttpResponse(render_pdf(template_name, context), content_type="application/pdf")
    disposition = "attachment" if download else "inline"
    response["Content-Disposition"] = f'{disposition}; filename="{filename}"'
    return response
