"""
编号生成器 - 实现本厂编号规则：AAAA-BB-CCCC-DDDD
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
import re


class NumberGenerator:
    """编号生成器"""
    
    @staticmethod
    def generate_factory_number(
        prefix: str,  # AAAA部分：前缀（如HS10表示10系列）
        category: str,  # BB部分：类别（如04表示4层板）
        sequence: int,  # CCCC部分：序号
        suffix: str = ""  # DDDD部分：后缀（如工艺代码）
    ) -> str:
        """
        生成本厂编号：AAAA-BB-CCCC-DDDD
        
        示例：
        - HS10-04-0001-ENIGAB01 (10系列4层板，序号0001，沉金工艺)
        - HS20-08-0123-HASL (20系列8层板，序号0123，有铅喷锡)
        """
        # 格式化各部分
        prefix_part = prefix.upper()[:4].ljust(4, 'X')  # AAAA，不足4位用X补齐
        category_part = category.upper()[:2].ljust(2, '0')  # BB，不足2位用0补齐
        sequence_part = str(sequence).zfill(4)  # CCCC，4位数字，不足补0
        suffix_part = suffix.upper()[:4] if suffix else ""  # DDDD，最多4位
        
        if suffix_part:
            return f"{prefix_part}-{category_part}-{sequence_part}-{suffix_part}"
        else:
            return f"{prefix_part}-{category_part}-{sequence_part}"
    
    @staticmethod
    def parse_factory_number(number: str) -> dict:
        """
        解析本厂编号
        
        返回: {
            'prefix': 'HS10',
            'category': '04',
            'sequence': 1,
            'suffix': 'ENIGAB01'
        }
        """
        pattern = r'^([A-Z0-9]{4})-([A-Z0-9]{2})-(\d{4})(?:-([A-Z0-9]{1,4}))?$'
        match = re.match(pattern, number.upper())
        
        if not match:
            raise ValueError(f"无效的编号格式: {number}")
        
        return {
            'prefix': match.group(1),
            'category': match.group(2),
            'sequence': int(match.group(3)),
            'suffix': match.group(4) or ''
        }
    
    @staticmethod
    def get_next_sequence(
        db: Session,
        table_class,
        prefix: str,
        category: str,
        year: Optional[int] = None
    ) -> int:
        """
        获取下一个序号
        
        Args:
            db: 数据库会话
            table_class: 表模型类
            prefix: 前缀
            category: 类别
            year: 年份（可选，用于按年重置序号）
        """
        if year is None:
            year = datetime.now().year
        
        # 查询该前缀和类别下的最大序号
        # 这里假设表有一个number字段存储编号
        # 实际使用时需要根据具体表结构调整
        max_number = db.query(
            func.max(table_class.number)
        ).filter(
            table_class.number.like(f"{prefix}-{category}-%")
        ).scalar()
        
        if max_number:
            parsed = NumberGenerator.parse_factory_number(max_number)
            return parsed['sequence'] + 1
        else:
            return 1
    
    @staticmethod
    def generate_quotation_number(db: Session, customer_id: str) -> str:
        """生成报价单号：QT-YYYYMMDD-XXXX"""
        today = datetime.now()
        date_part = today.strftime("%Y%m%d")
        
        # 查询当天的最大序号（延迟导入避免循环依赖）
        try:
            from backend.common.models.sd import Quotation
            max_number = db.query(
                func.max(Quotation.quotation_number)
            ).filter(
                Quotation.quotation_number.like(f"QT-{date_part}-%")
            ).scalar()
            
            if max_number:
                sequence = int(max_number.split('-')[-1]) + 1
            else:
                sequence = 1
        except:
            sequence = 1
        
        return f"QT-{date_part}-{sequence:04d}"
    
    @staticmethod
    def generate_sales_order_number(db: Session) -> str:
        """生成销售订单号：SO-YYYYMMDD-XXXX"""
        today = datetime.now()
        date_part = today.strftime("%Y%m%d")
        
        try:
            from backend.common.models.sd import SalesOrder
            max_number = db.query(
                func.max(SalesOrder.order_number)
            ).filter(
                SalesOrder.order_number.like(f"SO-{date_part}-%")
            ).scalar()
            
            if max_number:
                sequence = int(max_number.split('-')[-1]) + 1
            else:
                sequence = 1
        except:
            sequence = 1
        
        return f"SO-{date_part}-{sequence:04d}"
    
    @staticmethod
    def generate_production_order_number(db: Session) -> str:
        """生成生产订单号：PO-YYYYMMDD-XXXX"""
        today = datetime.now()
        date_part = today.strftime("%Y%m%d")
        
        try:
            from backend.common.models.pp import ProductionOrder
            max_number = db.query(
                func.max(ProductionOrder.order_number)
            ).filter(
                ProductionOrder.order_number.like(f"PO-{date_part}-%")
            ).scalar()
            
            if max_number:
                sequence = int(max_number.split('-')[-1]) + 1
            else:
                sequence = 1
        except:
            sequence = 1
        
        return f"PO-{date_part}-{sequence:04d}"
    
    @staticmethod
    def generate_lot_number(db: Session) -> str:
        """生成LOT卡号：LOT-YYYYMMDD-XXXX"""
        today = datetime.now()
        date_part = today.strftime("%Y%m%d")
        
        try:
            from backend.common.models.pp import LotCard
            max_number = db.query(
                func.max(LotCard.lot_number)
            ).filter(
                LotCard.lot_number.like(f"LOT-{date_part}-%")
            ).scalar()
            
            if max_number:
                sequence = int(max_number.split('-')[-1]) + 1
            else:
                sequence = 1
        except:
            sequence = 1
        
        return f"LOT-{date_part}-{sequence:04d}"

    @staticmethod
    def generate_document_number(
        db: Session,
        model_class,
        field_name: str,
        prefix: str,
        digits: int = 4,
        date_part: Optional[str] = None
    ) -> str:
        """通用单据号生成：PREFIX-YYYYMMDD-XXXX（或 NNN）。

        用于计划/成本域新增单据，避免每张单据重复实现计数逻辑。
        """
        if date_part is None:
            date_part = datetime.now().strftime("%Y%m%d")
        field = getattr(model_class, field_name)
        pattern = f"{prefix}-{date_part}-%"
        max_number = db.query(func.max(field)).filter(field.like(pattern)).scalar()
        if max_number:
            try:
                sequence = int(str(max_number).split('-')[-1]) + 1
            except (TypeError, ValueError):
                sequence = 1
        else:
            sequence = 1
        return f"{prefix}-{date_part}-{sequence:0{digits}d}"

