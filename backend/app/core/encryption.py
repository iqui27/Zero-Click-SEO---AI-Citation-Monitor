"""
Encryption utilities for sensitive data like OAuth tokens.
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def get_encryption_key() -> bytes:
    """
    Obtém a chave de criptografia do ambiente.
    Se não existir, gera uma nova (apenas para desenvolvimento).
    """
    key_str = os.getenv("ENCRYPTION_KEY")
    
    if not key_str:
        # Desenvolvimento: gerar chave temporária
        print("[ENCRYPTION] WARNING: No ENCRYPTION_KEY found, generating temporary key")
        return Fernet.generate_key()
    
    # Derivar chave de 32 bytes a partir da string
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'seo_analyzer_salt',  # Salt fixo (em produção, usar salt único por instalação)
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(key_str.encode()))
    return key


def encrypt_token(token: str) -> str:
    """
    Criptografa um token OAuth2.
    
    Args:
        token: Token em formato JSON string
        
    Returns:
        Token criptografado em base64
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted = f.encrypt(token.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        print(f"[ENCRYPTION] Error encrypting token: {e}")
        raise


def decrypt_token(encrypted_token: str) -> str:
    """
    Descriptografa um token OAuth2.
    
    Args:
        encrypted_token: Token criptografado em base64
        
    Returns:
        Token original em formato JSON string
    """
    try:
        key = get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_token.encode())
        decrypted = f.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        print(f"[ENCRYPTION] Error decrypting token: {e}")
        raise
