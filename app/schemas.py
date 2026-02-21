from pydantic import BaseModel, validator
from typing import List, Optional

# 图片上传响应模型
class ImageUploadResponse(BaseModel):
    success: bool
    file_path: Optional[str] = None
    message: Optional[str] = None

# 单条论文数据
class PaperItem(BaseModel):
    title: str
    journal: Optional[str] = None
    publish_date: Optional[str] = None
    images: List[str] = []  # 图片路径列表

# 单条资政报告数据
class PolicyItem(BaseModel):
    title: str
    adopt_unit: Optional[str] = None
    submit_date: Optional[str] = None
    images: List[str] = []

# 单条学术交流数据
class AcademicItem(BaseModel):
    name: str
    participate_type: Optional[str] = None
    exchange_date: Optional[str] = None
    images: List[str] = []

# 单条志愿服务数据
class VolunteerItem(BaseModel):
    project_name: str
    hours: Optional[str] = None
    service_date: Optional[str] = None
    images: List[str] = []
    
    @validator('hours')
    def validate_hours(cls, v):
        if v and not v.replace('.', '').isdigit():
            raise ValueError('服务时长必须为数字')
        return v

# 单条获奖数据
class AwardItem(BaseModel):
    name: str
    level: Optional[str] = None
    award_date: Optional[str] = None
    images: List[str] = []

# 提交所有数据的请求模型
class AchievementSubmitRequest(BaseModel):
    openid: Optional[str] = "test_openid"  # 小程序用户openid
    paperList: List[PaperItem] = []
    policyList: List[PolicyItem] = []
    academicList: List[AcademicItem] = []
    volunteerList: List[VolunteerItem] = []
    awardList: List[AwardItem] = []

# 提交响应模型
class AchievementSubmitResponse(BaseModel):
    success: bool
    message: str
    achievement_id: Optional[int] = None