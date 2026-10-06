from django import forms

from dossiers.models import StatutDossier

from .models import DossierEvent, TypeEvenement


class DossierEventForm(forms.ModelForm):
    changer_statut = forms.ChoiceField(
        label="Passer le dossier au statut",
        choices=[("", "— Ne pas changer —")] + list(StatutDossier.choices),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = DossierEvent
        fields = ["type_evenement", "date_evenement", "lieu", "commentaire"]
        widgets = {
            "type_evenement": forms.Select(attrs={"class": "form-select"}),
            "date_evenement": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "lieu": forms.TextInput(attrs={"class": "form-control", "placeholder": "Port, aéroport, entrepôt..."}),
            "commentaire": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Status changes are logged automatically; users record them via `changer_statut`.
        self.fields["type_evenement"].choices = [
            c for c in TypeEvenement.choices if c[0] != TypeEvenement.CHANGEMENT_STATUT
        ]
        self.fields["date_evenement"].input_formats = ["%Y-%m-%dT%H:%M"]
