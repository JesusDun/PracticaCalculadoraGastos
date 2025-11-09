import json
import io
import csv
from abc import ABC, abstractmethod
from datetime import datetime

class Reporte(ABC):
    def __init__(self, datos):
        self.datos = datos

    @abstractmethod
    def generar_reporte(self):
        pass
    
    @abstractmethod
    def get_mimetype(self):
        pass

    @abstractmethod
    def get_filename(self):
        pass

class ReporteCSV(Reporte):
    def generar_reporte(self):
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Descripcion', 'Monto', 'Categoria', 'Fecha'])
        if not self.datos:
            return output.getvalue()
        for gasto in self.datos:
            writer.writerow([
                gasto['id'], gasto['descripcion'], gasto['monto'], 
                gasto['categoria'], gasto['fecha']
            ])
        return output.getvalue()

    def get_mimetype(self):
        return 'text/csv'

    def get_filename(self):
        return 'gastos.csv'

class ReporteJSON(Reporte):
    def generar_reporte(self):
        return json.dumps(self.datos, indent=4)

    def get_mimetype(self):
        return 'application/json'

    def get_filename(self):
        return 'gastos.json'

class ReporteDecorator(Reporte):
    _reporte_envuelto: Reporte = None

    def __init__(self, reporte: Reporte) -> None:
        self._reporte_envuelto = reporte
        super().__init__(reporte.datos)

    @property
    def reporte(self) -> Reporte:
        return self._reporte_envuelto

    def generar_reporte(self):
        return self._reporte_envuelto.generar_reporte()

    def get_mimetype(self):
        return self._reporte_envuelto.get_mimetype()

    def get_filename(self):
        return self._reporte_envuelto.get_filename()

class ReporteConEncabezado(ReporteDecorator):
    def __init__(self, reporte: Reporte, username: str):
        super().__init__(reporte)
        self.username = username
        self.fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def generar_reporte(self):
        contenido_original = self.reporte.generar_reporte()
        
        if isinstance(self.reporte, ReporteCSV):
            encabezado = f"Reporte de Gastos para: {self.username}\n"
            encabezado += f"Fecha de Generación: {self.fecha_actual}\n\n"
            return encabezado + contenido_original
        
        elif isinstance(self.reporte, ReporteJSON):
            datos_decorados = {
                "generado_por": self.username,
                "fecha_reporte": self.fecha_actual,
                "gastos": json.loads(contenido_original)
            }
            return json.dumps(datos_decorados, indent=4)
        
        return contenido_original

    def get_filename(self):
        nombre_original = self.reporte.get_filename()
        return f"Reporte_{self.username}_{nombre_original}"

class ReportFactory:
    def crear_reporte(self, tipo, datos):
        if tipo == 'csv':
            return ReporteCSV(datos)
        elif tipo == 'json':
            return ReporteJSON(datos)
        else:
            raise ValueError("Tipo de reporte no válido")
