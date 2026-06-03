from uuid import UUID

from fastapi import APIRouter, Query, HTTPException, Request
from sqlalchemy import select, func

from app.api.deps import CurrentUser, DBSession
from app.models.risk_rule import RiskRule
from app.models.alert import Alert
from app.schemas.common import ResponseBase, PageResponse
from app.schemas.risk import RiskRuleCreate, RiskRuleUpdate, RiskRuleResponse, AlertResponse
from app.services.risk_service import mark_all_alerts_read, get_unread_count
from app.services.audit_service import log_action, extract_request_info

router = APIRouter()


@router.get("/rules", response_model=ResponseBase[list[RiskRuleResponse]])
async def list_rules(user: CurrentUser, db: DBSession):
    result = await db.execute(
        select(RiskRule)
        .where(RiskRule.user_id == user.id)
        .order_by(RiskRule.priority.asc(), RiskRule.created_at.desc())
    )
    rules = result.scalars().all()
    return ResponseBase(data=[RiskRuleResponse.model_validate(r) for r in rules])


@router.post("/rules", response_model=ResponseBase[RiskRuleResponse], status_code=201)
async def create_rule(user: CurrentUser, db: DBSession, payload: RiskRuleCreate, request: Request):
    count_result = await db.scalar(
        select(func.count(RiskRule.id)).where(RiskRule.user_id == user.id)
    )
    max_rules = 30 if payload.strategy_id is None else 20
    if (count_result or 0) >= max_rules:
        raise HTTPException(status_code=400, detail=f"规则数量已达上限({max_rules}条)")

    rule = RiskRule(
        user_id=user.id,
        strategy_id=str(payload.strategy_id) if payload.strategy_id else None,
        rule_type=payload.rule_type,
        params=payload.params,
        priority=payload.priority,
    )
    db.add(rule)
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="risk.rule_create", resource_type="risk_rule", resource_id=str(rule.id), detail={"rule_type": payload.rule_type}, ip_address=ip, user_agent=ua)

    return ResponseBase(data=RiskRuleResponse.model_validate(rule))


@router.put("/rules/{rule_id}", response_model=ResponseBase[RiskRuleResponse])
async def update_rule(
    user: CurrentUser,
    db: DBSession,
    rule_id: UUID,
    payload: RiskRuleUpdate,
    request: Request,
):
    rule = await db.get(RiskRule, rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(status_code=404, detail="规则不存在")
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(rule, key, value)
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="risk.rule_update", resource_type="risk_rule", resource_id=str(rule_id), ip_address=ip, user_agent=ua)

    return ResponseBase(data=RiskRuleResponse.model_validate(rule))


@router.patch("/rules/{rule_id}/toggle", response_model=ResponseBase[RiskRuleResponse])
async def toggle_rule(user: CurrentUser, db: DBSession, rule_id: UUID):
    rule = await db.get(RiskRule, rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(status_code=404, detail="规则不存在")
    rule.enabled = not rule.enabled
    await db.flush()
    return ResponseBase(data=RiskRuleResponse.model_validate(rule))


@router.delete("/rules/{rule_id}", response_model=ResponseBase[None])
async def delete_rule(user: CurrentUser, db: DBSession, rule_id: UUID, request: Request):
    rule = await db.get(RiskRule, rule_id)
    if not rule or rule.user_id != user.id:
        raise HTTPException(status_code=404, detail="规则不存在")
    await db.delete(rule)
    await db.flush()

    ip, ua = extract_request_info(request)
    await log_action(db, user_id=user.id, action="risk.rule_delete", resource_type="risk_rule", resource_id=str(rule_id), ip_address=ip, user_agent=ua)

    return ResponseBase()


@router.get("/alerts", response_model=ResponseBase[PageResponse[AlertResponse]])
async def list_alerts(
    user: CurrentUser,
    db: DBSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    level: str | None = Query(None),
    read: bool | None = Query(None),
):
    query = select(Alert).where(Alert.user_id == user.id)
    count_query = select(func.count(Alert.id)).where(Alert.user_id == user.id)
    if level:
        query = query.where(Alert.level == level)
        count_query = count_query.where(Alert.level == level)
    if read is not None:
        query = query.where(Alert.read == read)
        count_query = count_query.where(Alert.read == read)

    total = await db.scalar(count_query)
    offset = (page - 1) * page_size
    query = query.order_by(Alert.created_at.desc()).offset(offset).limit(page_size)
    result = await db.execute(query)
    alerts = result.scalars().all()

    total_pages = (total + page_size - 1) // page_size if total else 0
    return ResponseBase(
        data=PageResponse(
            items=[AlertResponse.model_validate(a) for a in alerts],
            total=total or 0,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    )


@router.put("/alerts/{alert_id}/read", response_model=ResponseBase[None])
async def mark_alert_read(user: CurrentUser, db: DBSession, alert_id: UUID):
    alert = await db.get(Alert, alert_id)
    if not alert or alert.user_id != user.id:
        raise HTTPException(status_code=404, detail="告警不存在")
    alert.read = True
    await db.flush()
    return ResponseBase()


@router.post("/alerts/read-all", response_model=ResponseBase[dict])
async def mark_all_read(user: CurrentUser, db: DBSession):
    count = await mark_all_alerts_read(db, user.id)
    return ResponseBase(data={"count": count})


@router.get("/alerts/unread-count", response_model=ResponseBase[dict])
async def unread_count(user: CurrentUser, db: DBSession):
    count = await get_unread_count(db, user.id)
    return ResponseBase(data={"count": count})
