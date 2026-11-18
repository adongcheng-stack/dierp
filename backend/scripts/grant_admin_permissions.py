"""
为admin用户赋予所有角色操作权限的脚本

此脚本确保admin用户存在且角色为ADMIN，ADMIN角色在系统中拥有所有权限。
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy.orm import sessionmaker
from backend.common.database.base import engine
from backend.common.models.user import User, UserRole
from backend.api.routers.auth import get_password_hash

def grant_admin_permissions():
    """确保admin用户存在且角色为ADMIN"""
    print("=" * 50)
    print("为admin用户赋予所有角色操作权限")
    print("=" * 50)
    print()
    
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # 检查admin用户是否存在
        admin = db.query(User).filter(User.username == "admin").first()
        
        if admin:
            # 如果存在，确保角色为ADMIN
            if admin.role != UserRole.ADMIN:
                print(f"[更新] admin用户角色从 {admin.role.value} 更新为 ADMIN")
                admin.role = UserRole.ADMIN
                admin.is_active = True
                admin.updated_by = "system"
                db.commit()
                print("[OK] admin用户角色已更新为ADMIN")
            else:
                print("[OK] admin用户已存在，角色为ADMIN")
            
            # 确保用户是激活状态
            if not admin.is_active:
                print("[更新] 激活admin用户")
                admin.is_active = True
                admin.updated_by = "system"
                db.commit()
                print("[OK] admin用户已激活")
        else:
            # 如果不存在，创建admin用户
            print("[创建] 创建admin用户")
            admin = User(
                username="admin",
                email="admin@hserp.com",
                password_hash=get_password_hash("admin123"),
                full_name="系统管理员",
                role=UserRole.ADMIN,
                department="IT",
                is_active=True,
                created_by="system"
            )
            db.add(admin)
            db.commit()
            print("[OK] admin用户创建成功！")
            print("  用户名: admin")
            print("  密码: admin123")
            print("  角色: ADMIN（拥有所有权限）")
        
        print()
        print("=" * 50)
        print("权限说明：")
        print("=" * 50)
        print("ADMIN角色拥有以下权限：")
        print("1. 可以执行所有角色的操作（销售、工程、生产、物料等）")
        print("2. 可以审批所有需要特定角色的流程")
        print("3. 可以管理用户和角色")
        print("4. 可以访问所有模块和功能")
        print()
        print("权限检查已通过以下方式实现：")
        print("- 使用 require_role() 函数时，ADMIN角色自动绕过所有限制")
        print("- 使用 require_any_role() 函数时，ADMIN角色自动绕过所有限制")
        print("- 使用 has_role() 或 has_any_role() 函数时，ADMIN角色返回True")
        print()
        print("=" * 50)
        print("操作完成！")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"[ERROR] 操作失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    grant_admin_permissions()

