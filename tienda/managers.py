from django.contrib.auth.base_user import BaseUserManager

class UsuarioManager(BaseUserManager):
    def create_user(self, numero, nombre, apellido, password=None, **extra_fields):
        if not numero:
            raise ValueError('El número de teléfono es obligatorio')
        if len(str(numero)) != 10:
            raise ValueError('El número debe tener 10 dígitos')
        user = self.model(
            numero=numero,
            nombre=nombre,
            apellido=apellido,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, numero, nombre, apellido, password=None, **extra_fields):
        extra_fields.setdefault('es_admin', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(numero, nombre, apellido, password, **extra_fields)
