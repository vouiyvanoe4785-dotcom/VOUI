from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import CashAccountForm, CashTransactionForm, TransferForm
from .models import CashAccount, CashTransaction, TypeMouvement


class BillingAccessMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.can_manage_billing()


class CashAccountListView(LoginRequiredMixin, BillingAccessMixin, ListView):
    model = CashAccount
    template_name = "treasury/account_list.html"
    context_object_name = "accounts"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["solde_global"] = sum((a.solde for a in self.object_list), 0)
        return ctx


class CashAccountDetailView(LoginRequiredMixin, BillingAccessMixin, DetailView):
    model = CashAccount
    template_name = "treasury/account_detail.html"
    context_object_name = "account"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mouvements"] = self.object.mouvements.select_related("dossier", "tiers")[:100]
        return ctx


class CashAccountCreateView(LoginRequiredMixin, BillingAccessMixin, CreateView):
    model = CashAccount
    form_class = CashAccountForm
    template_name = "treasury/account_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Caisse / compte créé avec succès.")
        return super().form_valid(form)


class CashAccountUpdateView(LoginRequiredMixin, BillingAccessMixin, UpdateView):
    model = CashAccount
    form_class = CashAccountForm
    template_name = "treasury/account_form.html"

    def form_valid(self, form):
        messages.success(self.request, "Caisse / compte mis à jour.")
        return super().form_valid(form)


class CashTransactionCreateView(LoginRequiredMixin, BillingAccessMixin, View):
    template_name = "treasury/transaction_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.account = get_object_or_404(CashAccount, pk=kwargs["account_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, account_pk):
        form = CashTransactionForm()
        return render(request, self.template_name, {"form": form, "account": self.account})

    def post(self, request, account_pk):
        form = CashTransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.compte = self.account
            transaction.created_by = request.user
            transaction.save()
            messages.success(request, "Mouvement enregistré.")
            return redirect("treasury:account_detail", pk=self.account.pk)
        return render(request, self.template_name, {"form": form, "account": self.account})


class TransferCreateView(LoginRequiredMixin, BillingAccessMixin, View):
    template_name = "treasury/transfer_form.html"

    def get(self, request):
        form = TransferForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = TransferForm(request.POST)
        if form.is_valid():
            source = form.cleaned_data["compte_source"]
            destination = form.cleaned_data["compte_destination"]
            montant = form.cleaned_data["montant"]
            date_mouvement = form.cleaned_data["date_mouvement"]
            description = form.cleaned_data["description"] or (
                f"Virement {source} -> {destination}"
            )

            sortie = CashTransaction.objects.create(
                compte=source, type_mouvement=TypeMouvement.SORTIE,
                categorie="virement_interne", montant=montant, date_mouvement=date_mouvement,
                description=description, created_by=request.user,
            )
            entree = CashTransaction.objects.create(
                compte=destination, type_mouvement=TypeMouvement.ENTREE,
                categorie="virement_interne", montant=montant, date_mouvement=date_mouvement,
                description=description, created_by=request.user, transfer_ref=sortie,
            )
            sortie.transfer_ref = entree
            sortie.save(update_fields=["transfer_ref"])

            messages.success(request, "Virement interne enregistré.")
            return redirect("treasury:account_list")
        return render(request, self.template_name, {"form": form})
