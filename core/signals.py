"""Sinyal autentikasi -> audit keamanan (login berhasil/gagal/logout)."""
from django.contrib.auth.signals import (
    user_logged_in, user_logged_out, user_login_failed,
)
from django.dispatch import receiver

from core.audit import log_event


@receiver(user_logged_in, dispatch_uid='core.audit.login_success')
def audit_login_success(sender, request, user, **kwargs):
    log_event('LOGIN_SUCCESS', request=request, actor=user,
              target=getattr(user, 'get_username', lambda: '')(), success=True)


@receiver(user_login_failed, dispatch_uid='core.audit.login_failed')
def audit_login_failed(sender, credentials, request=None, **kwargs):
    username = ''
    if isinstance(credentials, dict):
        username = credentials.get('username') or credentials.get('email') or ''
    # JANGAN pernah menyimpan password dari credentials.
    log_event('LOGIN_FAILED', request=request, target=username, success=False,
              metadata={'reason': 'invalid_credentials'})


@receiver(user_logged_out, dispatch_uid='core.audit.logout')
def audit_logout(sender, request, user, **kwargs):
    log_event('LOGOUT', request=request, actor=user,
              target=getattr(user, 'get_username', lambda: '')() if user else '',
              success=True)
