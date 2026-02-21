import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 图片上传配置
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)  # 自动创建上传目录
MAX_FILE_SIZE = 5 * 1024 * 1024  # 最大文件大小：5MB
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif"}

# 数据库配置
DATABASE_URL = f"sqlite:///{BASE_DIR / 'student_stats.db'}"

# CORS 配置（允许小程序前端跨域）
CORS_ORIGINS = [
    "http://localhost",
    "http://localhost:8000",
    "https://servicewechat.com"  # 微信小程序跨域允许
]