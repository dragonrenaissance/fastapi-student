# app/main.py 完整版本（关联学生学号）
from fastapi import FastAPI, Depends, Body, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta
import jwt
import bcrypt
import os
import uuid
from typing import List, Optional
from fastapi.security import OAuth2PasswordBearer  # 关键：导入OAuth2PasswordBearer

# ========== 数据库模型导入 & 配置 ==========
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey

# 基础模型类
Base = declarative_base()

# 1. 学生用户表（注册/登录）
class StudentUser(Base):
    __tablename__ = "student_users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, comment="学生姓名")
    student_id = Column(String(20), unique=True, nullable=False, comment="学号（唯一）")
    password = Column(String(100), nullable=False, comment="加密后的密码")
    create_time = Column(DateTime, default=datetime.now, comment="注册时间")
    is_active = Column(Boolean, default=True, comment="是否激活")

# 2. 成果主表（关联学生学号）
class StudentAchievement(Base):
    __tablename__ = "student_achievements"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(20), nullable=False, comment="关联的学生学号")
    openid = Column(String(100), nullable=True, comment="小程序OpenID（可选）")
    create_time = Column(DateTime, default=datetime.now, comment="提交时间")
    audit_status = Column(Boolean, default=False, comment="审核状态：False未审核/True已审核")
    audit_note = Column(String(200), nullable=True, comment="审核备注")
    audit_time = Column(DateTime, nullable=True, comment="审核时间")

# 3. 论文表
class Paper(Base):
    __tablename__ = "paper"
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"), nullable=False, comment="关联成果主表ID")
    title = Column(String(200), nullable=False, comment="论文标题")
    journal = Column(String(100), nullable=True, comment="发表期刊")
    publish_date = Column(String(20), nullable=True, comment="发表日期")

# 4. 资政报告表
class PolicyReport(Base):
    __tablename__ = "policy_report"
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"), nullable=False, comment="关联成果主表ID")
    title = Column(String(200), nullable=False, comment="报告标题")
    adopt_unit = Column(String(100), nullable=True, comment="采纳单位")
    submit_date = Column(String(20), nullable=True, comment="提交日期")

# 5. 学术交流表
class AcademicExchange(Base):
    __tablename__ = "academic_exchange"
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"), nullable=False, comment="关联成果主表ID")
    name = Column(String(200), nullable=False, comment="交流名称")
    participate_type = Column(String(50), nullable=True, comment="参与类型")
    exchange_date = Column(String(20), nullable=True, comment="交流日期")

# 6. 志愿服务表
class VolunteerService(Base):
    __tablename__ = "volunteer_service"
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"), nullable=False, comment="关联成果主表ID")
    project_name = Column(String(200), nullable=False, comment="项目名称")
    hours = Column(Integer, default=0, comment="服务时长")
    service_date = Column(String(20), nullable=True, comment="服务日期")

# 7. 获奖表
class Award(Base):
    __tablename__ = "award"
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, ForeignKey("student_achievements.id"), nullable=False, comment="关联成果主表ID")
    name = Column(String(200), nullable=False, comment="奖项名称")
    level = Column(String(50), nullable=True, comment="奖项级别")
    award_date = Column(String(20), nullable=True, comment="获奖日期")

# 8. 图片表
class AchievementImage(Base):
    __tablename__ = "achievement_image"
    id = Column(Integer, primary_key=True, index=True)
    achievement_id = Column(Integer, nullable=True, comment="关联成果主表ID")
    paper_id = Column(Integer, nullable=True, comment="关联论文ID")
    policy_id = Column(Integer, nullable=True, comment="关联资政报告ID")
    academic_id = Column(Integer, nullable=True, comment="关联学术交流ID")
    volunteer_id = Column(Integer, nullable=True, comment="关联志愿服务ID")
    award_id = Column(Integer, nullable=True, comment="关联获奖ID")
    file_path = Column(String(200), nullable=False, comment="图片文件路径")

# ========== FastAPI 初始化 ==========
app = FastAPI(title="学生成果管理系统", version="1.0")

# 跨域配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境可指定具体域名）
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有HTTP方法
    allow_headers=["*"],  # 允许所有请求头
)

# ========== 数据库连接配置 ==========
# SQLite数据库路径
DATABASE_URL = "sqlite:///./student_status.db"
# 创建数据库引擎（SQLite需添加check_same_thread=False）
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 依赖：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== JWT 配置（登录Token） ==========
SECRET_KEY = "your-secret-key-20260221"  # 替换为随机字符串（建议用：openssl rand -hex 32）
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # Token有效期2小时
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/student/login")
# ========== 图片上传配置 ==========
# 上传目录（确保存在）
UPLOAD_DIR = "./uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

# ========== 接口定义 ==========
# 1. 测试接口
@app.get("/test")
async def test_api():
    return {"message": "服务器正常运行", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

# 2. 学生注册接口
@app.post("/student/register")
async def student_register(
    name: str = Body(...),
    student_id: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # 校验学号是否已存在
        existing_student = db.query(StudentUser).filter(StudentUser.student_id == student_id).first()
        if existing_student:
            return {
                "success": False,
                "message": "该学号已注册，请直接登录"
            }
        
        # 密码加密（bcrypt）
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
        
        # 存储注册信息
        new_student = StudentUser(
            name=name,
            student_id=student_id,
            password=hashed_password,
            create_time=datetime.now(),
            is_active=True
        )
        db.add(new_student)
        db.commit()
        db.refresh(new_student)
        
        return {
            "success": True,
            "message": "注册成功，请登录",
            "student_id": student_id
        }
    except Exception as e:
        db.rollback()
        print(f"注册失败：{str(e)}")
        return {
            "success": False,
            "message": f"注册失败：{str(e)}"
        }

# 3. 学生登录接口
@app.post("/student/login")
async def student_login(
    student_id: str = Body(...),
    password: str = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # 查询学生信息
        student = db.query(StudentUser).filter(StudentUser.student_id == student_id).first()
        if not student:
            return {
                "success": False,
                "message": "学号未注册，请先注册"
            }
        
        # 校验密码
        password_bytes = password.encode('utf-8')
        hashed_password_bytes = student.password.encode('utf-8')
        if not bcrypt.checkpw(password_bytes, hashed_password_bytes):
            return {
                "success": False,
                "message": "密码错误"
            }
        
        # 生成Token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = jwt.encode(
            {
                "sub": student.student_id,
                "name": student.name,
                "exp": datetime.utcnow() + access_token_expires
            },
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        
        return {
            "success": True,
            "message": "登录成功",
            "token": access_token,
            "student_id": student.student_id,
            "name": student.name
        }
    except Exception as e:
        print(f"登录失败：{str(e)}")
        return {
            "success": False,
            "message": f"登录失败：{str(e)}"
        }

# 验证token并获取当前学生
async def get_current_student(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=401,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        student_id: str = payload.get("sub")
        if student_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    # 从数据库查询学生信息
    student = db.query(StudentUser).filter(
        StudentUser.student_id == student_id,
        StudentUser.is_active == True
    ).first()
    
    if student is None:
        raise credentials_exception
    return student

# 获取学生信息接口（首页调用）
@app.get("/api/student/info", summary="获取当前登录学生信息")
async def get_student_info(
    current_student: StudentUser = Depends(get_current_student)
):
    # 返回前端需要的字段（对应前端的 studentName/studentId）
    return {
        "code": 200,
        "message": "获取成功",
        "data": {
            "studentName": current_student.name,    # 对应前端 studentName
            "studentId": current_student.student_id # 对应前端 studentId
        }
    }


# 4. 图片上传接口
@app.post("/upload/image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # 生成唯一文件名（避免重复）
        file_ext = file.filename.split(".")[-1]
        file_name = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        
        # 保存文件
        with open(file_path, "wb") as f:
            f.write(await file.read())
        
        return {
            "success": True,
            "file_name": file_name,
            "file_path": file_name,  # 返回相对路径，前端拼接完整URL
            "message": "图片上传成功"
        }
    except Exception as e:
        print(f"图片上传失败：{str(e)}")
        return {
            "success": False,
            "message": f"图片上传失败：{str(e)}"
        }

# 5. 成果提交接口（关联学生学号）
@app.post("/submit/achievements")
async def submit_achievements(
    # 核心：接收学生学号
    student_id: str = Body(...),
    # 各类成果数据
    paperList: List[dict] = Body(...),
    policyList: List[dict] = Body(...),
    academicList: List[dict] = Body(...),
    volunteerList: List[dict] = Body(...),
    awardList: List[dict] = Body(...),
    db: Session = Depends(get_db)
):
    try:
        # 校验学号是否为注册用户（可选）
        student = db.query(StudentUser).filter(StudentUser.student_id == student_id).first()
        if not student:
            return {
                "success": False,
                "message": "学号未注册，无法提交成果"
            }
        
        # 创建成果主记录（关联学号）
        achievement = StudentAchievement(
            student_id=student_id,
            create_time=datetime.now(),
            audit_status=False
        )
        db.add(achievement)
        db.commit()
        db.refresh(achievement)
        achievement_id = achievement.id

        # 处理论文数据
        for paper in paperList:
            if paper.get("title"):  # 非空才存储
                new_paper = Paper(
                    achievement_id=achievement_id,
                    title=paper.get("title"),
                    journal=paper.get("journal"),
                    publish_date=paper.get("date")
                )
                db.add(new_paper)
                db.commit()
                db.refresh(new_paper)
                
                # 处理论文图片
                for img_path in paper.get("images", []):
                    if img_path:
                        new_img = AchievementImage(
                            achievement_id=achievement_id,
                            paper_id=new_paper.id,
                            file_path=img_path
                        )
                        db.add(new_img)

        # 处理资政报告数据
        for policy in policyList:
            if policy.get("title"):
                new_policy = PolicyReport(
                    achievement_id=achievement_id,
                    title=policy.get("title"),
                    adopt_unit=policy.get("adopt_unit"),
                    submit_date=policy.get("date")
                )
                db.add(new_policy)
                db.commit()
                db.refresh(new_policy)
                
                # 处理资政报告图片
                for img_path in policy.get("images", []):
                    if img_path:
                        new_img = AchievementImage(
                            achievement_id=achievement_id,
                            policy_id=new_policy.id,
                            file_path=img_path
                        )
                        db.add(new_img)

        # 处理学术交流数据
        participate_types = ['参会', '报告发言', '墙报展示', '其他']
        for academic in academicList:
            if academic.get("name"):
                new_academic = AcademicExchange(
                    achievement_id=achievement_id,
                    name=academic.get("name"),
                    participate_type=participate_types[int(academic.get("typeIndex", 0))],
                    exchange_date=academic.get("date")
                )
                db.add(new_academic)
                db.commit()
                db.refresh(new_academic)
                
                # 处理学术交流图片
                for img_path in academic.get("images", []):
                    if img_path:
                        new_img = AchievementImage(
                            achievement_id=achievement_id,
                            academic_id=new_academic.id,
                            file_path=img_path
                        )
                        db.add(new_img)

        # 处理志愿服务数据
        for volunteer in volunteerList:
            if volunteer.get("project_name"):
                new_volunteer = VolunteerService(
                    achievement_id=achievement_id,
                    project_name=volunteer.get("project_name"),
                    hours=int(volunteer.get("hours", 0)),
                    service_date=volunteer.get("date")
                )
                db.add(new_volunteer)
                db.commit()
                db.refresh(new_volunteer)
                
                # 处理志愿服务图片
                for img_path in volunteer.get("images", []):
                    if img_path:
                        new_img = AchievementImage(
                            achievement_id=achievement_id,
                            volunteer_id=new_volunteer.id,
                            file_path=img_path
                        )
                        db.add(new_img)

        # 处理获奖数据
        award_levels = ['校级', '市级', '省级', '国家级', '国际级']
        for award in awardList:
            if award.get("name"):
                new_award = Award(
                    achievement_id=achievement_id,
                    name=award.get("name"),
                    level=award_levels[int(award.get("levelIndex", 0))],
                    award_date=award.get("date")
                )
                db.add(new_award)
                db.commit()
                db.refresh(new_award)
                
                # 处理获奖图片
                for img_path in award.get("images", []):
                    if img_path:
                        new_img = AchievementImage(
                            achievement_id=achievement_id,
                            award_id=new_award.id,
                            file_path=img_path
                        )
                        db.add(new_img)

        # 提交所有数据
        db.commit()
        
        return {
            "success": True,
            "message": "成果提交成功，等待审核",
            "achievement_id": achievement_id,
            "student_id": student_id
        }
    except Exception as e:
        db.rollback()
        print(f"提交成果失败：{str(e)}")
        return {
            "success": False,
            "message": f"提交失败：{str(e)}"
        }



# 6. 管理端：获取成果列表（支持学号/审核状态筛选）
@app.get("/admin/achievements")
async def get_achievements(
    page: int = 1,
    size: int = 10,
    audit_status: Optional[bool] = None,
    student_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    try:
        # 构建查询条件
        query = db.query(StudentAchievement)
        
        # 审核状态筛选
        if audit_status is not None:
            query = query.filter(StudentAchievement.audit_status == audit_status)
        
        # 学号筛选
        if student_id and student_id.strip():
            query = query.filter(StudentAchievement.student_id == student_id.strip())
        
        # 分页处理
        total = query.count()
        achievements = query.order_by(StudentAchievement.create_time.desc()).offset((page-1)*size).limit(size).all()
        
        # 组装返回数据
        result = []
        for item in achievements:
            result.append({
                "id": item.id,
                "student_id": item.student_id,
                "openid": item.openid,
                "create_time": item.create_time.strftime("%Y-%m-%d %H:%M:%S") if item.create_time else "",
                "audit_status": item.audit_status,
                "audit_note": item.audit_note or "",
                "audit_time": item.audit_time.strftime("%Y-%m-%d %H:%M:%S") if item.audit_time else ""
            })
        
        return {
            "code": 200,
            "data": {
                "list": result,
                "total": total,
                "page": page,
                "size": size
            },
            "message": "查询成功"
        }
    except Exception as e:
        print(f"查询成果列表失败：{str(e)}")
        return {
            "code": 500,
            "data": {
                "list": [],
                "total": 0,
                "page": page,
                "size": size
            },
            "message": f"查询失败：{str(e)}"
        }

# 7. 管理端：获取成果详情
@app.get("/admin/achievements/{achievement_id}")
async def get_achievement_detail(
    achievement_id: int,
    db: Session = Depends(get_db)
):
    try:
        # 查询主记录
        achievement = db.query(StudentAchievement).filter(StudentAchievement.id == achievement_id).first()
        if not achievement:
            return {
                "code": 404,
                "data": None,
                "message": "成果记录不存在"
            }
        
        # 查询各类子数据
        papers = db.query(Paper).filter(Paper.achievement_id == achievement_id).all()
        policies = db.query(PolicyReport).filter(PolicyReport.achievement_id == achievement_id).all()
        academics = db.query(AcademicExchange).filter(AcademicExchange.achievement_id == achievement_id).all()
        volunteers = db.query(VolunteerService).filter(VolunteerService.achievement_id == achievement_id).all()
        awards = db.query(Award).filter(Award.achievement_id == achievement_id).all()
        
        # 格式化数据（含图片）
        def format_items(items, item_type):
            result = []
            for item in items:
                # 查询图片
                img_query = db.query(AchievementImage)
                if item_type == "paper":
                    img_query = img_query.filter(AchievementImage.paper_id == item.id)
                elif item_type == "policy":
                    img_query = img_query.filter(AchievementImage.policy_id == item.id)
                elif item_type == "academic":
                    img_query = img_query.filter(AchievementImage.academic_id == item.id)
                elif item_type == "volunteer":
                    img_query = img_query.filter(AchievementImage.volunteer_id == item.id)
                elif item_type == "award":
                    img_query = img_query.filter(AchievementImage.award_id == item.id)
                
                images = img_query.all()
                # 拼接完整图片URL（替换为你的后端IP）
                img_paths = [
                    f"http://localhost:8000/uploads/{img.file_path}" 
                    for img in images
                ]
                
                # 组装数据
                item_data = {
                    "id": item.id,
                    "images": img_paths
                }
                if item_type == "paper":
                    item_data.update({
                        "title": item.title,
                        "journal": item.journal,
                        "publish_date": item.publish_date
                    })
                elif item_type == "policy":
                    item_data.update({
                        "title": item.title,
                        "adopt_unit": item.adopt_unit,
                        "submit_date": item.submit_date
                    })
                elif item_type == "academic":
                    item_data.update({
                        "name": item.name,
                        "participate_type": item.participate_type,
                        "exchange_date": item.exchange_date
                    })
                elif item_type == "volunteer":
                    item_data.update({
                        "project_name": item.project_name,
                        "hours": item.hours,
                        "service_date": item.service_date
                    })
                elif item_type == "award":
                    item_data.update({
                        "name": item.name,
                        "level": item.level,
                        "award_date": item.award_date
                    })
                result.append(item_data)
            return result
        
        # 组装最终返回数据
        return {
            "code": 200,
            "data": {
                "id": achievement.id,
                "student_id": achievement.student_id,
                "create_time": achievement.create_time.strftime("%Y-%m-%d %H:%M:%S") if achievement.create_time else "",
                "audit_status": achievement.audit_status,
                "audit_note": achievement.audit_note or "",
                "audit_time": achievement.audit_time.strftime("%Y-%m-%d %H:%M:%S") if achievement.audit_time else "",
                "papers": format_items(papers, "paper"),
                "policies": format_items(policies, "policy"),
                "academics": format_items(academics, "academic"),
                "volunteers": format_items(volunteers, "volunteer"),
                "awards": format_items(awards, "award")
            },
            "message": "查询成功"
        }
    except Exception as e:
        print(f"查询成果详情失败：{str(e)}")
        return {
            "code": 500,
            "data": None,
            "message": f"查询失败：{str(e)}"
        }

# 8. 管理端：审核成果
@app.post("/admin/achievements/{achievement_id}/audit")
async def audit_achievement(
    achievement_id: int,
    data: dict = Body(...),
    db: Session = Depends(get_db)
):
    try:
        achievement = db.query(StudentAchievement).filter(StudentAchievement.id == achievement_id).first()
        if not achievement:
            return {
                "code": 404,
                "data": None,
                "message": "成果记录不存在"
            }
        
        # 更新审核信息
        achievement.audit_status = data.get("audit_status", False)
        achievement.audit_note = data.get("audit_note", "")
        achievement.audit_time = datetime.now()
        
        db.commit()
        db.refresh(achievement)
        
        return {
            "code": 200,
            "message": "审核成功",
            "data": {
                "id": achievement.id,
                "student_id": achievement.student_id,
                "audit_status": achievement.audit_status
            }
        }
    except Exception as e:
        db.rollback()
        print(f"审核成果失败：{str(e)}")
        return {
            "code": 500,
            "data": None,
            "message": f"审核失败：{str(e)}"
        }

# 9. 静态文件访问（图片预览）
@app.get("/uploads/{file_name}")
async def get_uploaded_file(file_name: str):
    file_path = os.path.join(UPLOAD_DIR, file_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path)

# ========== 启动时创建数据库表 ==========
@app.on_event("startup")
async def startup():
    # 创建所有表（如果不存在）
    Base.metadata.create_all(bind=engine)
    print("数据库表初始化完成")

# ========== 新增：管理端-获取提交成果的学生列表 ==========
@app.get("/admin/students", response_model=dict)
async def get_student_list(
    page: int = 1,
    size: int = 10,
    student_id: str = None,
    name: str = None,
    audit_status: bool = None,
    db: Session = Depends(get_db)
):
    try:
        # 1. 查询所有提交过成果的学生（去重）
        sub_query = db.query(StudentAchievement.student_id).distinct().subquery()
        query = db.query(StudentUser)
        query = query.filter(StudentUser.student_id.in_(sub_query))
        
        # 2. 添加筛选条件
        if student_id and student_id.strip():
            query = query.filter(StudentUser.student_id.like(f"%{student_id.strip()}%"))
        if name and name.strip():
            query = query.filter(StudentUser.name.like(f"%{name.strip()}%"))
        
        # 3. 分页处理
        total = query.count()
        students = query.offset((page-1)*size).limit(size).all()
        
        # 4. 组装数据（补充成果数和审核状态）
        result = []
        for student in students:
            # 统计该学生的成果数
            achievement_count = db.query(StudentAchievement).filter(
                StudentAchievement.student_id == student.student_id
            ).count()
            
            # 最后提交时间
            last_achievement = db.query(StudentAchievement).filter(
                StudentAchievement.student_id == student.student_id
            ).order_by(StudentAchievement.create_time.desc()).first()
            last_submit_time = last_achievement.create_time.strftime("%Y-%m-%d %H:%M:%S") if last_achievement else ""
            
            # 审核状态（是否全部审核）
            all_audited = db.query(StudentAchievement).filter(
                StudentAchievement.student_id == student.student_id,
                StudentAchievement.audit_status == False
            ).count() == 0
            
            result.append({
                "student_id": student.student_id,
                "name": student.name,
                "submit_count": achievement_count,
                "last_submit_time": last_submit_time,
                "audit_status": all_audited
            })
        
        return {
            "code": 200,
            "data": {
                "list": result,
                "total": total,
                "page": page,
                "size": size
            },
            "message": "查询成功"
        }
    except Exception as e:
        print(f"查询学生列表失败：{str(e)}")
        return {
            "code": 500,
            "data": {
                "list": [],
                "total": 0
            },
            "message": f"查询失败：{str(e)}"
        }

# ========== 新增：管理端-获取学生基础信息 ==========
@app.get("/admin/students/{student_id}", response_model=dict)
async def get_student_info(
    student_id: str,
    db: Session = Depends(get_db)
):
    try:
        # 查询学生基础信息
        student = db.query(StudentUser).filter(StudentUser.student_id == student_id).first()
        if not student:
            return {
                "code": 404,
                "data": None,
                "message": "学生不存在"
            }
        
        # 统计该学生的成果总数
        total_achievements = db.query(StudentAchievement).filter(
            StudentAchievement.student_id == student_id
        ).count()
        
        # 整体审核状态（是否全部审核）
        all_audited = db.query(StudentAchievement).filter(
            StudentAchievement.student_id == student_id,
            StudentAchievement.audit_status == False
        ).count() == 0
        
        return {
            "code": 200,
            "data": {
                "student_id": student.student_id,
                "name": student.name,
                "total_achievements": total_achievements,
                "audit_status": all_audited
            },
            "message": "查询成功"
        }
    except Exception as e:
        print(f"查询学生信息失败：{str(e)}")
        return {
            "code": 500,
            "data": None,
            "message": f"查询失败：{str(e)}"
        }


# ========== 主函数（直接运行） ==========
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)