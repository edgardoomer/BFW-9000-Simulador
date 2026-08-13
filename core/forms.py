from django import forms

from .models import ParametrosEconomicos, Proyecto


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = [
            "id_proyecto", "nombre", "fecha", "operadora", "bloque", "campo",
            "yacimiento", "pozos", "area_acres", "unidad_coord", "descripcion",
            "h_def", "phi_def", "swi_def", "sor_def", "k_def",
            "muw_def", "muo_def", "bo_def", "bw_def",
            "presion_def", "temperatura_def", "api_def", "rw_def",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def clean(self):
        datos = super().clean()
        swi, sor = datos.get("swi_def"), datos.get("sor_def")
        if swi is not None and sor is not None and swi + sor >= 1:
            raise forms.ValidationError(
                f"Swi + Sor = {swi + sor:.2f}. Debe ser menor que 1 para que "
                "exista saturación móvil."
            )
        phi = datos.get("phi_def")
        if phi is not None and not (0 < phi < 1):
            self.add_error("phi_def", "La porosidad debe estar entre 0 y 1.")
        return datos


class EconomiaForm(forms.ModelForm):
    class Meta:
        model = ParametrosEconomicos
        exclude = ["proyecto", "actualizado"]

    def clean_regalia(self):
        v = self.cleaned_data["regalia"]
        if not (0 <= v < 1):
            raise forms.ValidationError("La regalía es una fracción entre 0 y 1.")
        return v
