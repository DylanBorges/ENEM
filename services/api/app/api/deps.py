from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.config import settings
from app.core.security import decode_token
from app.db.session import get_db
from app.models.auth_institution import User, UserRole, Membership

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas ou token expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Conta inativa",
        )
    return user


def require_role(*allowed_roles: UserRole):
    """Garante RBAC para endpoints restritos."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles and current_user.role != UserRole.PLATFORM_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente para este recurso",
            )
        return current_user
    return role_checker


def check_institution_access(
    institution_id: str,
    user: User,
    db: Session,
) -> Membership:
    """Verificação rigorosa de isolamento multi-tenant:

    Instituição A JAMAIS pode ler ou alterar dados de Instituição B.
    """
    if user.role == UserRole.PLATFORM_ADMIN:
        membership = db.scalar(
            select(Membership).where(
                Membership.institution_id == institution_id,
                Membership.user_id == user.id,
            )
        )
        if not membership:
            # Platform admin tem acesso global sintetizado
            return Membership(user_id=user.id, institution_id=institution_id, role=UserRole.PLATFORM_ADMIN)
        return membership

    membership = db.scalar(
        select(Membership).where(
            Membership.institution_id == institution_id,
            Membership.user_id == user.id,
        )
    )
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado aos dados desta instituição (violação multi-tenant)",
        )
    return membership
