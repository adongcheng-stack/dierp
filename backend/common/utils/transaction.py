"""
事务管理装饰器
"""
from functools import wraps
from typing import Callable, Any
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger("hserp.transaction")


def transactional(func: Callable) -> Callable:
    """
    事务管理装饰器
    
    自动处理数据库事务的提交和回滚
    
    Usage:
        @transactional
        async def create_order(order_data: dict, db: Session):
            # 业务逻辑
            db.add(order)
            # 不需要手动commit，装饰器会自动处理
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        db: Session = None
        
        # 查找db参数
        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break
        
        if not db:
            db = kwargs.get('db')
        
        if not db:
            # 如果没有db参数，直接执行函数
            return await func(*args, **kwargs)
        
        try:
            result = await func(*args, **kwargs)
            db.commit()
            logger.debug(f"事务提交成功: {func.__name__}")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"事务回滚: {func.__name__} | error={str(e)}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        db: Session = None
        
        # 查找db参数
        for arg in args:
            if isinstance(arg, Session):
                db = arg
                break
        
        if not db:
            db = kwargs.get('db')
        
        if not db:
            # 如果没有db参数，直接执行函数
            return func(*args, **kwargs)
        
        try:
            result = func(*args, **kwargs)
            db.commit()
            logger.debug(f"事务提交成功: {func.__name__}")
            return result
        except Exception as e:
            db.rollback()
            logger.error(f"事务回滚: {func.__name__} | error={str(e)}")
            raise
    
    # 根据函数是否为协程返回对应的包装器
    import inspect
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

