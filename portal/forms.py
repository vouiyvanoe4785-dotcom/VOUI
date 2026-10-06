from django import forms


class ReponseDevisForm(forms.Form):
    decision = forms.ChoiceField(choices=[("accepter", "Accepter"), ("refuser", "Refuser")])
    nom = forms.CharField(
        label="Votre nom et prénom", max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "name"}),
    )
    accord = forms.BooleanField(
        label="J'accepte ce devis, son montant et ses conditions.", required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    commentaire = forms.CharField(
        label="Commentaire (facultatif)", required=False, max_length=2000,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2}),
    )

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("decision") == "accepter" and not cleaned.get("accord"):
            self.add_error("accord", "Cochez la case pour confirmer votre accord.")
        return cleaned
