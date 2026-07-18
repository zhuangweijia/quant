BCRYPT_MAX_PASSWORD_BYTES = 72


def validate_bcrypt_password_size(password: str) -> str:
    if len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("密码 UTF-8 编码不能超过 72 字节")
    return password
