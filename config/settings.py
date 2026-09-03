"""Project settings for the student material archive system."""

import os
from ipaddress import IPv4Address, AddressValueError
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str = "") -> str:
    """按“系统环境变量 > .env > 默认值”的顺序读取配置。"""
    return os.environ.get(name, _ENV_FILE_VALUES.get(name, default))


def env_bool(name: str, default: bool = False) -> bool:
    raw = env(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name}必须是布尔值。")


def env_list(name: str, default: str = "") -> list[str]:
    raw = env(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def env_int(name: str, default: int) -> int:
    raw = env(name, str(default)).strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name}必须是整数。") from exc


def env_path(name: str, default: Path) -> Path:
    return Path(env(name, str(default))).expanduser()


def load_dotenv(env_file: Path | None = None) -> dict[str, str]:
    """读取简单 KEY=VALUE 格式的 .env，供Windows本地开发使用。"""
    values: dict[str, str] = {}
    env_file = env_file or BASE_DIR / ".env"
    if not env_file.exists():
        return values
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_ENV_FILE_VALUES = load_dotenv()

PRODUCTION = env_bool("DJANGO_PRODUCTION", False)
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.accounts",
    "apps.students",
    "apps.materials",
    "apps.imports",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": env_path("DJANGO_SQLITE_PATH", BASE_DIR / "db.sqlite3"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = env_path("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles")
MEDIA_URL = "/media/"
MEDIA_ROOT = env_path("DJANGO_MEDIA_ROOT", BASE_DIR / "media")
BACKUP_ROOT = env_path("DJANGO_BACKUP_ROOT", BASE_DIR / "backups")

# V1.4 首版生产环境固定使用公网 IPv4 的 HTTP 入口，由安全组限制访问来源。
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

LOG_LEVEL = env("DJANGO_LOG_LEVEL", "INFO" if PRODUCTION else "WARNING").upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{asctime} {levelname} {name} {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.AdminUser"
LOGIN_URL = "accounts:admin_login"
LOGIN_REDIRECT_URL = "students:admin_student_list"


def validate_production_settings() -> None:
    if not PRODUCTION:
        return

    problems: list[str] = []
    if DEBUG:
        problems.append("DJANGO_DEBUG必须为False")
    if SECRET_KEY in {
        "dev-only-change-me",
        "replace-with-at-least-50-random-characters",
    } or len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5 or SECRET_KEY.startswith(
        "django-insecure-"
    ):
        problems.append("DJANGO_SECRET_KEY必须设置为至少50字符且具有足够随机性的生产密钥")
    public_ipv4: str | None = None
    if len(ALLOWED_HOSTS) != 1 or "*" in ALLOWED_HOSTS:
        problems.append("DJANGO_ALLOWED_HOSTS必须且只能配置一个固定公网IPv4地址")
    else:
        try:
            address = IPv4Address(ALLOWED_HOSTS[0])
            if not address.is_global:
                problems.append("DJANGO_ALLOWED_HOSTS必须使用固定公网IPv4地址")
            else:
                public_ipv4 = str(address)
        except AddressValueError:
            problems.append("DJANGO_ALLOWED_HOSTS必须使用合法IPv4地址")
    if public_ipv4 and CSRF_TRUSTED_ORIGINS != [f"http://{public_ipv4}"]:
        problems.append("DJANGO_CSRF_TRUSTED_ORIGINS必须且只能配置为http://<固定公网IPv4>")
    elif not public_ipv4 and not CSRF_TRUSTED_ORIGINS:
        problems.append("DJANGO_CSRF_TRUSTED_ORIGINS必须显式配置")

    configured_paths = {
        "DJANGO_SQLITE_PATH": Path(DATABASES["default"]["NAME"]),
        "DJANGO_STATIC_ROOT": STATIC_ROOT,
        "DJANGO_MEDIA_ROOT": MEDIA_ROOT,
        "DJANGO_BACKUP_ROOT": BACKUP_ROOT,
    }
    for name, path in configured_paths.items():
        if name not in os.environ and name not in _ENV_FILE_VALUES:
            problems.append(f"{name}在生产环境必须显式配置")
        if not path.is_absolute():
            problems.append(f"{name}在生产环境必须是绝对路径")

    if LOG_LEVEL not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        problems.append("DJANGO_LOG_LEVEL不是有效日志级别")

    if problems:
        raise ImproperlyConfigured("生产配置无效：" + "；".join(problems))


validate_production_settings()
