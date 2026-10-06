from django.db import transaction


def save_document_with_lines(request, form, formset_class):
    """Validate a document form and its line formset together, then save both atomically.

    Returns (document, formset): document is None when anything is invalid, in which
    case nothing has been written (no orphan header, no reference number consumed).
    """
    form_valid = form.is_valid()  # also fills form.instance from the submitted data
    formset = formset_class(request.POST, instance=form.instance)
    if not (form_valid and formset.is_valid()):
        return None, formset

    with transaction.atomic():
        document = form.save(commit=False)
        if not document.created_by_id:
            document.created_by = request.user
        document.save()
        formset.instance = document
        formset.save()
    return document, formset
