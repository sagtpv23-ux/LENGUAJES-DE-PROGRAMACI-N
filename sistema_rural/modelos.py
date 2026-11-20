from abc import ABC, abstractmethod
from datetime import date
from enum import Enum

from .excepciones import (ErrorSistemaRural, MedicamentoNoEncontradoError,
                          StockInsuficienteError)
from .seguridad import enmascarar_dni, hash_dni
from .validaciones import (validar_colegiatura, validar_entero, validar_fecha_nacimiento,
                           validar_nombre_medicamento, validar_nombre_persona,
                           validar_texto_libre)


class Persona(ABC):
    """Clase base abstracta (no se instancia directamente). Guarda el DNI solo como hash y enmascarado."""

    def __init__(self, dni: str, nombres: str, apellidos: str):
        self._dni_hash = hash_dni(dni)            # encapsulado: sin setter
        self._dni_enmascarado = enmascarar_dni(dni)
        self.nombres = nombres
        self.apellidos = apellidos

    @property
    def nombres(self) -> str:
        return self._nombres

    @nombres.setter
    def nombres(self, valor):
        self._nombres = validar_nombre_persona(valor, "Los nombres")

    @property
    def apellidos(self) -> str:
        return self._apellidos

    @apellidos.setter
    def apellidos(self, valor):
        self._apellidos = validar_nombre_persona(valor, "Los apellidos")

    @property
    def dni_hash(self) -> str:
        return self._dni_hash

    @property
    def dni_enmascarado(self) -> str:
        return self._dni_enmascarado

    @property
    def nombre_completo(self) -> str:
        return f"{self._nombres} {self._apellidos}"

    @abstractmethod
    def rol(self) -> str:
        """Polimorfismo: cada subclase declara su rol."""

    def __repr__(self) -> str:  # nunca incluye el DNI completo
        return f"<{self.rol()} {self.dni_enmascarado}>"


class Paciente(Persona):
    def __init__(self, dni, nombres, apellidos, fecha_nacimiento):
        super().__init__(dni, nombres, apellidos)
        self._fecha_nacimiento = validar_fecha_nacimiento(fecha_nacimiento)
        self._diagnosticos = []   # lista de textos; es un dato sensible de salud

    def rol(self) -> str:
        return "Paciente"

    def edad(self, referencia=None):
        # Si no se indica una fecha de referencia, se usa la fecha de hoy
        ref = referencia or date.today()
        f = self._fecha_nacimiento
        return ref.year - f.year - ((ref.month, ref.day) < (f.month, f.day))

    def agregar_diagnostico(self, texto: str) -> None:
        self._diagnosticos.append(validar_texto_libre(texto, "El diagnóstico", 3, 200))

    @property
    def diagnosticos(self) -> tuple:
        return tuple(self._diagnosticos)      # copia inmutable


class PersonalSalud(Persona, ABC):
    def __init__(self, dni, nombres, apellidos, colegiatura):
        super().__init__(dni, nombres, apellidos)
        self._colegiatura = validar_colegiatura(colegiatura)

    @property
    def colegiatura(self) -> str:
        return self._colegiatura

    @abstractmethod
    def puede_prescribir(self) -> bool:
        ...


class Medico(PersonalSalud):
    def rol(self) -> str:
        return "Médico"

    def puede_prescribir(self) -> bool:
        return True


class Enfermero(PersonalSalud):
    def rol(self) -> str:
        return "Enfermero"

    def puede_prescribir(self) -> bool:
        return False


class EstadoCita(Enum):
    """Enumeración: lista cerrada de estados posibles de una cita."""
    PROGRAMADA = "programada"
    ATENDIDA = "atendida"
    CANCELADA = "cancelada"


class Cita:
    def __init__(self, id_cita, paciente, personal, fecha_hora, motivo):
        self._id = id_cita
        self._paciente = paciente
        self._personal = personal
        self._fecha_hora = fecha_hora
        self._motivo = validar_texto_libre(motivo, "El motivo", 3, 100)
        self._estado = EstadoCita.PROGRAMADA

    # Getters (solo lectura): se accede como cita.id, cita.estado, etc.
    @property
    def id(self):
        return self._id

    @property
    def paciente(self):
        return self._paciente

    @property
    def personal(self):
        return self._personal

    @property
    def fecha_hora(self):
        return self._fecha_hora

    @property
    def motivo(self):
        return self._motivo

    @property
    def estado(self):
        return self._estado

    def atender(self) -> None:
        self._cambiar_estado(EstadoCita.ATENDIDA)

    def cancelar(self) -> None:
        self._cambiar_estado(EstadoCita.CANCELADA)

    def _cambiar_estado(self, nuevo):
        if self._estado is not EstadoCita.PROGRAMADA:
            raise ErrorSistemaRural(f"La cita {self._id} ya está {self._estado.value}.")
        self._estado = nuevo


class Medicamento:
    def __init__(self, nombre, stock, stock_minimo=10):
        self._nombre = validar_nombre_medicamento(nombre)
        self._stock = validar_entero(stock, "El stock", 0)
        self._stock_minimo = validar_entero(stock_minimo, "El stock mínimo", 0)

    @property
    def nombre(self):
        return self._nombre

    @property
    def stock(self):
        return self._stock

    @property
    def stock_minimo(self):
        return self._stock_minimo

    @property
    def en_stock_critico(self) -> bool:
        return self._stock <= self._stock_minimo

    def retirar(self, cantidad):
        validar_entero(cantidad, "La cantidad", 1)
        if cantidad > self._stock:
            raise StockInsuficienteError(
                f"Stock insuficiente de {self._nombre}: hay {self._stock}.")
        self._stock -= cantidad

    def reponer(self, cantidad):
        validar_entero(cantidad, "La cantidad", 1)
        self._stock += cantidad


class Inventario:
    """Composición: el inventario crea y posee sus medicamentos."""

    def __init__(self):
        self._medicamentos = {}   # diccionario: nombre en minúsculas -> Medicamento

    def agregar(self, nombre, stock, stock_minimo=10):
        med = Medicamento(nombre, stock, stock_minimo)
        if med.nombre.lower() in self._medicamentos:
            raise ErrorSistemaRural(f"Ya existe el medicamento '{med.nombre}' en el inventario.")
        self._medicamentos[med.nombre.lower()] = med
        return med

    def obtener(self, nombre):
        try:
            return self._medicamentos[nombre.lower()]
        except KeyError:
            raise MedicamentoNoEncontradoError(f"'{nombre}' no está en el inventario.")

    def listar(self) -> tuple:
        return tuple(self._medicamentos.values())
