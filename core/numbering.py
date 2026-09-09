from django.utils import timezone


def generate_reference(model, prefix, field_name="reference", width=4):
    """
    Generate a sequential, human-readable reference such as AT-2026-0001,
    scoped to the current year, for the given model/field.
    """
    year = timezone.now().year
    year_prefix = f"{prefix}-{year}-"
    last = (
        model.objects.filter(**{f"{field_name}__startswith": year_prefix})
        .order_by(f"-{field_name}")
        .first()
    )
    if last:
        last_value = getattr(last, field_name)
        try:
            last_number = int(last_value.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            last_number = 0
    else:
        last_number = 0
    next_number = last_number + 1
    return f"{year_prefix}{str(next_number).zfill(width)}"
