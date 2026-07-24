"""Kapalı beta davet kodu ve Design Partner erişim endpoint'leri."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.middleware.auth import CurrentUser, get_current_user
from src.api.v1.schemas.beta import (
    BetaAccessResponse,
    BetaPartnerListResponse,
    InvitationCreateRequest,
    InvitationCreateResponse,
    InvitationListResponse,
    InvitationRedeemRequest,
    InvitationResponse,
)
from src.api.v1.schemas.common import ErrorResponse
from src.utils.beta_store import (
    BetaAccessAlreadyExistsError,
    BetaAccessNotFoundError,
    BetaAccessRecord,
    BetaStore,
    InvitationNotFoundError,
    InvitationRecord,
    InvitationRedeemError,
    get_beta_store,
)
from src.utils.logger import get_logger


logger = get_logger(__name__)
router = APIRouter()


def _require_admin(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    role = current_user.claims.get("role")
    if not isinstance(role, str) or role.casefold() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gerekli.",
        )
    return current_user


def _invitation_response(
    invitation: InvitationRecord,
    store: BetaStore,
) -> InvitationResponse:
    return InvitationResponse(
        invitation_id=invitation.invitation_id,
        partner_name=invitation.partner_name,
        created_by=invitation.created_by,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        max_uses=invitation.max_uses,
        use_count=invitation.use_count,
        status=invitation.status_at(store.now()),
        revoked_at=invitation.revoked_at,
        revoked_by=invitation.revoked_by,
    )


def _access_response(
    user_id: str,
    access: BetaAccessRecord | None,
) -> BetaAccessResponse:
    if access is None:
        return BetaAccessResponse(
            user_id=user_id,
            has_access=False,
            status="none",
        )

    return BetaAccessResponse(
        user_id=access.user_id,
        has_access=access.active,
        status=access.status,
        invitation_id=access.invitation_id,
        partner_name=access.partner_name,
        granted_at=access.granted_at,
        revoked_at=access.revoked_at,
        revoked_by=access.revoked_by,
    )


@router.post(
    "/invitations",
    response_model=InvitationCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Kapalı beta daveti oluştur",
    description=(
        "Yalnızca admin kullanıcıların Design Partner için süreli ve kullanım "
        "limitli bir davet kodu oluşturmasını sağlar. Ham kod yalnızca bu yanıtta "
        "gösterilir; store içinde sadece hash değeri saklanır."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
        403: {"model": ErrorResponse, "description": "Admin yetkisi gerekli"},
    },
)
def create_invitation(
    payload: InvitationCreateRequest,
    admin: CurrentUser = Depends(_require_admin),
    store: BetaStore = Depends(get_beta_store),
) -> InvitationCreateResponse:
    created = store.create_invitation(
        partner_name=payload.partner_name,
        created_by=admin.user_id,
        expires_in=timedelta(days=payload.expires_in_days),
        max_uses=payload.max_uses,
    )
    invitation = _invitation_response(created.invitation, store)

    logger.info(
        "Kapalı beta daveti oluşturuldu",
        extra={
            "invitation_id": invitation.invitation_id,
            "created_by": admin.user_id,
            "expires_at": invitation.expires_at.isoformat(),
            "max_uses": invitation.max_uses,
        },
    )

    return InvitationCreateResponse(
        **invitation.model_dump(),
        code=created.code,
    )


@router.get(
    "/invitations",
    response_model=InvitationListResponse,
    summary="Kapalı beta davetlerini listele",
    responses={
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
        403: {"model": ErrorResponse, "description": "Admin yetkisi gerekli"},
    },
)
def list_invitations(
    admin: CurrentUser = Depends(_require_admin),
    store: BetaStore = Depends(get_beta_store),
) -> InvitationListResponse:
    del admin
    invitations = [
        _invitation_response(record, store)
        for record in store.list_invitations()
    ]
    return InvitationListResponse(
        total=len(invitations),
        invitations=invitations,
    )


@router.delete(
    "/invitations/{invitation_id}",
    response_model=InvitationResponse,
    summary="Kapalı beta davetini iptal et",
    responses={
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
        403: {"model": ErrorResponse, "description": "Admin yetkisi gerekli"},
        404: {"model": ErrorResponse, "description": "Davet bulunamadı"},
    },
)
def revoke_invitation(
    invitation_id: str,
    admin: CurrentUser = Depends(_require_admin),
    store: BetaStore = Depends(get_beta_store),
) -> InvitationResponse:
    try:
        invitation = store.revoke_invitation(
            invitation_id,
            revoked_by=admin.user_id,
        )
    except InvitationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    logger.info(
        "Kapalı beta daveti iptal edildi",
        extra={
            "invitation_id": invitation.invitation_id,
            "revoked_by": admin.user_id,
        },
    )
    return _invitation_response(invitation, store)


@router.post(
    "/redeem",
    response_model=BetaAccessResponse,
    summary="Davet kodunu kullan",
    description=(
        "JWT ile doğrulanmış kullanıcı davet kodunu kullanarak Design Partner "
        "erişimi kazanır. Kullanıcı kimliği request body'den değil JWT'den alınır."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Kod kullanılamıyor"},
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
        409: {"model": ErrorResponse, "description": "Erişim zaten mevcut"},
    },
)
def redeem_invitation(
    payload: InvitationRedeemRequest,
    current_user: CurrentUser = Depends(get_current_user),
    store: BetaStore = Depends(get_beta_store),
) -> BetaAccessResponse:
    try:
        access = store.redeem_invitation(
            code=payload.code,
            user_id=current_user.user_id,
        )
    except InvitationRedeemError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except BetaAccessAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    logger.info(
        "Design Partner erişimi verildi",
        extra={
            "user_id": access.user_id,
            "invitation_id": access.invitation_id,
        },
    )
    return _access_response(current_user.user_id, access)


@router.get(
    "/access",
    response_model=BetaAccessResponse,
    summary="Kendi beta erişimini görüntüle",
    responses={
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
    },
)
def get_my_access(
    current_user: CurrentUser = Depends(get_current_user),
    store: BetaStore = Depends(get_beta_store),
) -> BetaAccessResponse:
    access = store.get_access(current_user.user_id)
    return _access_response(current_user.user_id, access)


@router.get(
    "/partners",
    response_model=BetaPartnerListResponse,
    summary="Design Partner erişimlerini listele",
    responses={
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
        403: {"model": ErrorResponse, "description": "Admin yetkisi gerekli"},
    },
)
def list_design_partners(
    include_revoked: bool = Query(
        default=False,
        description="İptal edilmiş erişimleri de listeye dahil et.",
    ),
    admin: CurrentUser = Depends(_require_admin),
    store: BetaStore = Depends(get_beta_store),
) -> BetaPartnerListResponse:
    del admin
    partners = [
        _access_response(record.user_id, record)
        for record in store.list_access_records(
            include_revoked=include_revoked,
        )
    ]
    return BetaPartnerListResponse(
        total=len(partners),
        partners=partners,
    )


@router.delete(
    "/partners/{user_id}",
    response_model=BetaAccessResponse,
    summary="Design Partner erişimini iptal et",
    responses={
        401: {"model": ErrorResponse, "description": "JWT gerekli"},
        403: {"model": ErrorResponse, "description": "Admin yetkisi gerekli"},
        404: {"model": ErrorResponse, "description": "Erişim bulunamadı"},
    },
)
def revoke_design_partner_access(
    user_id: str,
    admin: CurrentUser = Depends(_require_admin),
    store: BetaStore = Depends(get_beta_store),
) -> BetaAccessResponse:
    try:
        access = store.revoke_access(
            user_id,
            revoked_by=admin.user_id,
        )
    except BetaAccessNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    logger.info(
        "Design Partner erişimi iptal edildi",
        extra={
            "user_id": access.user_id,
            "revoked_by": admin.user_id,
        },
    )
    return _access_response(user_id, access)
