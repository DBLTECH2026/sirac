from django.db import models


class ConsultaIA(models.Model):
    """Registro de cada consulta a los modelos y algoritmos (trazabilidad)."""
    tipo = models.CharField(max_length=40)
    entrada = models.JSONField(default=dict)
    resultado = models.JSONField(default=dict)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creado"]
