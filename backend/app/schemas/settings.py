from datetime import datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.passwords import validate_bcrypt_password_size
from app.core.webhook_security import validate_webhook_url


class StrictSettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NotificationConfigRequest(StrictSettingsModel):
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = Field(default=465, ge=1, le=65535)
    email_sender: str = ""
    email_password: str = ""
    email_use_ssl: bool = True
    email_recipient: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    webhook_secret: str = ""
    notify_levels: list[Literal["info", "warning", "error"]] = Field(
        default_factory=lambda: ["warning", "error"]
    )

    @field_validator("webhook_url")
    @classmethod
    def valid_webhook_url(cls, value: str):
        return validate_webhook_url(value)


class NotificationConfigResponse(StrictSettingsModel):
    email_enabled: bool
    email_smtp_host: str
    email_smtp_port: int
    email_sender: str
    has_email_password: bool
    email_use_ssl: bool
    email_recipient: str
    webhook_enabled: bool
    webhook_url: str
    has_webhook_secret: bool
    notify_levels: list[Literal["info", "warning", "error"]]


class SystemParams(StrictSettingsModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    data_retention_days: int = Field(ge=7, le=3650)
    alert_retention_days: int = Field(ge=7, le=3650)
    model_train_window_days: int = Field(ge=252, le=2520)
    model_val_window_days: int = Field(ge=21, le=504)
    forward_return_days: int = Field(ge=1, le=30)
    forward_return_threshold: float = Field(gt=0, le=1)
    model_ic_threshold: float = Field(ge=0, le=1)
    stock_universe: Literal["csi300"] = "csi300"
    analysis_time: str

    @field_validator("model_val_window_days")
    @classmethod
    def validation_window_is_shorter(cls, value: int, info):
        training = info.data.get("model_train_window_days")
        if training is not None and value >= training:
            raise ValueError("验证窗口必须短于训练窗口")
        return value

    @field_validator("analysis_time")
    @classmethod
    def valid_analysis_time(cls, value: str):
        try:
            time.fromisoformat(value)
        except ValueError as exc:
            raise ValueError("分析时间必须为 HH:mm") from exc
        if len(value) != 5:
            raise ValueError("分析时间必须为 HH:mm")
        return value


class SystemParamsRequest(StrictSettingsModel):
    params: SystemParams


class ProfileResponse(StrictSettingsModel):
    username: str
    role: str
    is_active: bool
    created_at: datetime | None = None


class PasswordChangeRequest(StrictSettingsModel):
    old_password: str = Field(min_length=8, max_length=64)
    new_password: str = Field(min_length=8, max_length=64)
    confirm_password: str = Field(min_length=8, max_length=64)

    @field_validator("old_password", "new_password", "confirm_password")
    @classmethod
    def password_fits_bcrypt(cls, value: str):
        return validate_bcrypt_password_size(value)
