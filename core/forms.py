from django import forms

from .models import Societe


class SocieteForm(forms.ModelForm):
    class Meta:
        model = Societe
        exclude = ["updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "form-control", "rows": 3})
            elif isinstance(field.widget, forms.ClearableFileInput):
                field.widget.attrs.update({"class": "form-control"})
            else:
                field.widget.attrs.update({"class": "form-control"})
