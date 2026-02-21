from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from .config import DATABASE_URL
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
Base = declarative_base()
# 新增：学生用户表（存储注册信息）
class StudentUser(Base):
    __tablename__ = "student_users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="学生姓名")
    student_id = Column(String(20), unique=True, nullable=False, comment="学号（唯一）")
    password = Column(String(100), nullable=False, comment="加密后的密码")
    create_time = Column(DateTime, default=datetime.now, comment="注册时间")
    is_active = Column(Boolean, default=True, comment="是否激活")
# 学生成果主表（存储基础信息）
class StudentAchievement(Base):
    __tablename__ = "student_achievements"
    
    id = Column(Integer, primary_key=True, index=True)
    # 小程序用户标识（实际需替换为真实openid）
    student_id = Column(String(20), nullable=False, comment="关联的学生学号")  # 新增字段
    openid = Column(String(100), index=True, nullable=False, default="test_openid")
    create_time = Column(DateTime, default=datetime.now)
    audit_status = Column(Boolean, default=False)  # False=未审核，True=已审核
    audit_note = Column(Text, nullable=True)  # 审核备注
    audit_time = Column(DateTime, nullable=True)  # 审核时间
    # 关联各类成果
    papers = relationship("Paper", back_populates="achievement", cascade="all, delete-orphan")
    policies = relationship("PolicyReport", back_populates="achievement", cascade="all, delete-orphan")
    academics = relationship("AcademicExchange", back_populates="achievement", cascade="all, delete-orphan")
    volunteers = relationship("VolunteerService", back_populates="achievement", cascade="all, delete-orphan")
    awards = relationship("Award", back_populates="achievement", cascade="all, delete-orphan")

# 论文表
class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"))
    title = Column(String(255), nullable=False)
    journal = Column(String(255))
    publish_date = Column(String(50))
    
    # 关联主表和图片
    achievement = relationship("StudentAchievement", back_populates="papers")
    images = relationship("AchievementImage", back_populates="paper", cascade="all, delete-orphan")

# 资政报告表
class PolicyReport(Base):
    __tablename__ = "policy_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"))
    title = Column(String(255), nullable=False)
    adopt_unit = Column(String(255))
    submit_date = Column(String(50))
    
    achievement = relationship("StudentAchievement", back_populates="policies")
    images = relationship("AchievementImage", back_populates="policy", cascade="all, delete-orphan")

# 学术交流表
class AcademicExchange(Base):
    __tablename__ = "academic_exchanges"
    
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"))
    name = Column(String(255), nullable=False)
    participate_type = Column(String(50))  # 参会/报告发言等
    exchange_date = Column(String(50))
    
    achievement = relationship("StudentAchievement", back_populates="academics")
    images = relationship("AchievementImage", back_populates="academic", cascade="all, delete-orphan")

# 志愿服务表
class VolunteerService(Base):
    __tablename__ = "volunteer_services"
    
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"))
    project_name = Column(String(255), nullable=False)
    hours = Column(String(20))  # 服务时长
    service_date = Column(String(50))
    
    achievement = relationship("StudentAchievement", back_populates="volunteers")
    images = relationship("AchievementImage", back_populates="volunteer", cascade="all, delete-orphan")

# 获奖荣誉表
class Award(Base):
    __tablename__ = "awards"
    
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"))
    name = Column(String(255), nullable=False)
    level = Column(String(50))  # 校级/市级等
    award_date = Column(String(50))
    
    achievement = relationship("StudentAchievement", back_populates="awards")
    images = relationship("AchievementImage", back_populates="award", cascade="all, delete-orphan")

# 证明图片表
class AchievementImage(Base):
    __tablename__ = "achievement_images"
    
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(Text, nullable=False)  # 图片存储路径
    file_name = Column(String(255))
    
    # 关联各类成果（外键二选一）
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)
    policy_id = Column(Integer, ForeignKey("policy_reports.id"), nullable=True)
    academic_id = Column(Integer, ForeignKey("academic_exchanges.id"), nullable=True)
    volunteer_id = Column(Integer, ForeignKey("volunteer_services.id"), nullable=True)
    award_id = Column(Integer, ForeignKey("awards.id"), nullable=True)
    
    # 反向关联
    paper = relationship("Paper", back_populates="images")
    policy = relationship("PolicyReport", back_populates="images")
    academic = relationship("AcademicExchange", back_populates="images")
    volunteer = relationship("VolunteerService", back_populates="images")
    award = relationship("Award", back_populates="images")

# 创建数据库连接
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建所有表
def create_tables():
    Base.metadata.create_all(bind=engine)