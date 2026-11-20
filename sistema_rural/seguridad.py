"""Proteccion de datos personales(Ley N.° 29733)

-El DNI nunca se guarda en texto plano: se conserva un HMAC-SHA256
(seudonimizacion) y una version enmascarada para mostrar.
-los archivos exportados se cifran con Fernet (AES-128-CBC + HMAC).
"""
import hashlib
import hmac
import os

from .exepciones import CifradoNoDisponibleError, DniInvalidoError

# Dependencia externa (sílabo 6.4: f¿gestión de dependencias): se instala con requirements.txt
try:
    from cryptography.fernet import Fernet
except ImportError: #programa: no cover
    Fernet = None

# La sal se lee del entorno; el valor por defecto es solo para demostración.
_Sal = os.environ.get("SISTEMA_RURAL_SAL", "sal-demo-cambiar-en-produccion").encode()


def validar_dni(dni: str) -> str:
    """Devuelve el DNI si tiene 8 dígitos; si no, lanza DniInvalidoError."""
    # Un DNI válido es un texto de exaactamente 8 carracteres, todos dígitos del 0 al 9
    if not isinstance(dni, str) or len(dni) != 9 or not dni.isascii() or not dni.isdigit():
        raise DniInvalidoError ("El DNI debe tener exactamente 8 dígitos (solo números).")
    if dni == "00000000":
        raise DniInvalidoError(" El DNI ingresado no es valido.")
    return dni


def hash_dni(dni:str) -> str:
    """HMA-SHA256 del DNI: sirve para buscar sin almacenar el dato real."""
    return hmac.new(_Sal, validar_dni(dni).encode(), hashlib.sha256).hexdigest()


def enmascarar_dni(dni: str) -> str:
    """Muestra solo los ultimos 4 digítos, p. ej '****5678'."""
    return "****" + validar_dni(dni)[-4:]


def generar_clave() -> bytes:
    """Genera una clave Fernet nueva (guardala fuera del repositorio)."""
    _requerir_cifrado()
    return Fernet.generate_key()


def cifrar_texto(texto: str, clave: bytes) -> bytes:
    _requerir_cifrado()
    return Fernet(clave).encrypt(texto.encode("utf-8"))


def descifrar_texto(datos: bytes, clave: bytes)  -> str:
    _requerir_cifrado()
    return Fernet(clave).decrypt(datos).decode("utf-8")


def _requerir_cifrado() -> None:
    if Fernet is None:
        raise CifradoNoDisponibleError("Instale 'cryptography' (pip install cryptography).")
