from django import forms

from .models import ALLOWED_DOCUMENT_EXTENSIONS, Document


class DocumentForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["type_document", "libelle", "fichier", "date_document"]
        widgets = {
            "type_document": forms.Select(attrs={"class": "form-select"}),
            "libelle": forms.TextInput(attrs={"class": "form-control"}),
            "fichier": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ",".join(f".{ext}" for ext in ALLOWED_DOCUMENT_EXTENSIONS),
            }),
            "date_document": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }
        help_texts = {
            "fichier": "Formats acceptés : " + ", ".join(ALLOWED_DOCUMENT_EXTENSIONS) + ".",
        }
