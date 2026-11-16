"""CRM de SIRAC: usuarios por rol, catálogo, clientes (oportunidades), mensajes, historial y entrenamiento de Kinti."""
from django.conf import settings
from django.db import models
from django.utils import timezone


class Perfil(models.Model):
    ROLES = [("admin", "Administradora"), ("gerente", "Gerente comercial"), ("ventas", "Ventas")]
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="perfil", on_delete=models.CASCADE)
    rol = models.CharField(max_length=10, choices=ROLES, default="ventas")
    cargo = models.CharField(max_length=60, blank=True)
    zona = models.CharField(max_length=20, default="Lima")  # Lima | Provincia (para el reparto con Hill climbing)
    especialidad = models.CharField(max_length=20, default="cocina")  # cocina | menaje | hogar
    color = models.CharField(max_length=9, default="#0EB155")
    meta_mensual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    capacidad = models.PositiveIntegerField(default=12)

    @property
    def iniciales(self):
        partes = (self.usuario.get_full_name() or self.usuario.username).split()
        return "".join(p[0] for p in partes[:2]).upper()


class Producto(models.Model):
    nombre = models.CharField(max_length=80)
    categoria = models.CharField(max_length=20, default="cocina")
    detalle = models.CharField(max_length=80, blank=True)
    precio = models.DecimalField(max_digits=9, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    garantia_meses = models.PositiveIntegerField(default=12)
    foto = models.CharField(max_length=80, blank=True)
    palabras = models.CharField(max_length=200, help_text="Palabras con las que Kinti reconoce el producto, separadas por comas")
    mas_vendido = models.BooleanField(default=False)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cliente(models.Model):
    ETAPAS = [("nuevo", "Nuevo"), ("calificado", "Calificado por IA"), ("cotizado", "Cotización enviada"),
              ("ganado", "Venta cerrada"), ("perdido", "Perdido")]
    ORIGENES = [("meta", "Meta Ads"), ("google", "Google Ads"), ("organico", "Orgánico"), ("directo", "Directo")]
    nombre = models.CharField(max_length=80)
    telefono = models.CharField(max_length=20, blank=True)
    distrito = models.CharField(max_length=40, blank=True)
    provincia = models.BooleanField(default=False)
    origen = models.CharField(max_length=10, choices=ORIGENES, default="meta")
    campana = models.CharField(max_length=60, blank=True)
    producto = models.ForeignKey(Producto, null=True, blank=True, on_delete=models.SET_NULL)
    cantidad = models.PositiveIntegerField(default=1)
    delivery = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    etapa = models.CharField(max_length=12, choices=ETAPAS, default="nuevo")
    motivo_perdida = models.CharField(max_length=60, blank=True)
    vendedor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="clientes")
    kinti_activo = models.BooleanField(default=True)
    estado_conv = models.CharField(max_length=30, default="inicio")  # estado del grafo de conversación (ia.busqueda.FLUJO)
    pidio_precio = models.BooleanField(default=False)
    pidio_delivery = models.BooleanField(default=False)
    probabilidad = models.FloatField(null=True, blank=True)
    etiqueta_ia = models.CharField(max_length=10, blank=True)
    etiquetas = models.JSONField(default=list, blank=True)
    no_leidos = models.PositiveIntegerField(default=0)
    simulador = models.BooleanField(default=False)  # creado desde el simulador público de WhatsApp
    whatsapp_jid = models.CharField(max_length=60, blank=True, db_index=True)  # chat real por Evolution API
    creado = models.DateTimeField(default=timezone.now)
    actualizado = models.DateTimeField(default=timezone.now)
    cerrado = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-actualizado"]

    def __str__(self):
        return self.nombre


class Mensaje(models.Model):
    AUTORES = [("cliente", "Cliente"), ("kinti", "Kinti · IA"), ("vendedor", "Vendedor"), ("sistema", "Sistema"), ("nota", "Nota interna")]
    cliente = models.ForeignKey(Cliente, related_name="mensajes", on_delete=models.CASCADE)
    autor = models.CharField(max_length=10, choices=AUTORES)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    texto = models.TextField()
    producto = models.ForeignKey(Producto, null=True, blank=True, on_delete=models.SET_NULL)  # tarjeta de producto
    segundos_respuesta = models.FloatField(null=True, blank=True)
    externo_id = models.CharField(max_length=80, blank=True, db_index=True)  # id del mensaje en WhatsApp
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["creado", "id"]


class Evento(models.Model):
    """Historial de la oportunidad: creación, cambios de etapa, derivaciones, asignaciones, precio enviado, pago."""
    cliente = models.ForeignKey(Cliente, related_name="eventos", on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20)
    texto = models.CharField(max_length=200)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    creado = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-creado", "-id"]


class RespuestaKinti(models.Model):
    """Entrenamiento: respuestas que Kinti usa cuando el cliente escribe alguna de las palabras clave."""
    tema = models.CharField(max_length=60)
    palabras = models.CharField(max_length=250)
    respuesta = models.TextField()
    activa = models.BooleanField(default=True)
    usos = models.PositiveIntegerField(default=0)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["tema"]


class Ajuste(models.Model):
    """Ajustes del CRM que se cambian desde la pantalla (por ejemplo, el filtro de WhatsApp)."""
    clave = models.CharField(max_length=40, unique=True)
    valor = models.JSONField(default=dict)

    @classmethod
    def leer(cls, clave, defecto):
        a = cls.objects.filter(clave=clave).first()
        return {**defecto, **a.valor} if a else dict(defecto)

    @classmethod
    def guardar(cls, clave, valor):
        cls.objects.update_or_create(clave=clave, defaults={"valor": valor})
