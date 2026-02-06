import re
import html
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

class SecurityManager:
    """
    Gerenciador centralizado de medidas de segurança
    """
    
    @staticmethod
    def sanitize_input(text, max_length=500):
        """
        Sanitiza entrada de usuário removendo ou escapando conteúdo perigoso
        """
        if not text:
            return ""
        
        # Remove tags HTML
        clean_text = strip_tags(str(text))
        
        # Escapa caracteres especiais
        clean_text = html.escape(clean_text)
        
        # Limita o tamanho
        if len(clean_text) > max_length:
            clean_text = clean_text[:max_length]
            
        return clean_text
    
    @staticmethod
    def validate_username(username):
        """
        Valida formato do username
        """
        if not username or len(username) < 3:
            raise ValidationError("Username deve ter pelo menos 3 caracteres")
        
        if len(username) > 50:
            raise ValidationError("Username muito longo")
            
        # Permite apenas letras, números e alguns caracteres especiais
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError("Username contém caracteres inválidos")
        
        return username
    
    @staticmethod
    def validate_codigo_suporte(codigo):
        """
        Valida código de suporte
        """
        try:
            codigo_int = int(codigo)
            if codigo_int < 1000 or codigo_int > 99999:
                raise ValidationError("Código de suporte inválido")
            return codigo_int
        except (ValueError, TypeError):
            raise ValidationError("Código de suporte deve ser um número")
    
    @staticmethod
    def prevent_brute_force(request, operation_type, max_attempts=5, window_seconds=300):
        """
        Prevenção básica contra ataques de força bruta
        """
        from django.core.cache import cache
        
        key = f"brute_force_{operation_type}_{request.META.get('REMOTE_ADDR')}"
        attempts = cache.get(key, 0)
        
        if attempts >= max_attempts:
            return False
            
        cache.set(key, attempts + 1, window_seconds)
        return True
    
    @staticmethod
    def validate_uuid(uuid_string):
        """
        Valida formato UUID
        """
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        return bool(uuid_pattern.match(str(uuid_string)))

# Instância global
security = SecurityManager()