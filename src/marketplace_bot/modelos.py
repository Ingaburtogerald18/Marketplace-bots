"""Los datos con los que trabaja el bot."""
from dataclasses import dataclass, field
from pathlib import Path

ESTADOS_FB = ["Nuevo", "Usado - Como nuevo", "Usado - Buen estado", "Usado - Aceptable"]
MAX_FOTOS = 10  # limite de Facebook


@dataclass
class Plantilla:
    """Un articulo: una carpeta en publicaciones/ con datos.txt, descripcion.txt y fotos."""
    carpeta: Path
    titulo: str = ""
    precio: str = ""
    categoria: str = ""
    estado: str = "Nuevo"
    descripcion: str = ""
    fotos: list = field(default_factory=list)

    @property
    def nombre(self):
        return self.carpeta.name

    @property
    def portada(self):
        return self.fotos[0] if self.fotos else None


@dataclass
class Resultado:
    """Como le fue a un articulo en una corrida."""
    carpeta: str
    titulo: str = ""
    estado: str = "pendiente"  # pendiente | trabajando | publicado | probado | fallo | saltado
    detalle: str = ""
    captura: str = ""

    @property
    def ok(self):
        return self.estado in ("publicado", "probado")
