from .excepciones import TipoPersonalInvalidoError
from .modelos import Enfermero, Medico


class PersonalFactory:
    
    _TIPOS = {"medico": Medico, "enfermero": Enfermero}

    @classmethod   
    def registrar_tipo(cls, tipo, clase):
        """Registra un nuevo tipo sin modificar el código existente."""
        cls._TIPOS[tipo.strip().lower()] = clase

    @classmethod
    def crear(cls, tipo, dni, nombres, apellidos, colegiatura):
        clase = cls._TIPOS.get(str(tipo).strip().lower())
        if clase is None:
            raise TipoPersonalInvalidoError(f"Tipo de personal desconocido: {tipo}")
        return clase(dni, nombres, apellidos, colegiatura)
