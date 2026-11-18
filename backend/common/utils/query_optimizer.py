"""
查询性能优化工具
用于减少N+1查询问题，使用SQLAlchemy的预加载机制
"""
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager
from sqlalchemy.orm import Query
from typing import Type, TypeVar, List, Optional
from functools import wraps

T = TypeVar('T')


class QueryOptimizer:
    """查询优化器"""
    
    @staticmethod
    def optimize_customer_query(query: Query) -> Query:
        """
        优化客户查询，预加载关联数据
        
        Args:
            query: 客户查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            selectinload('addresses'),
            selectinload('contacts'),
            selectinload('partner_functions'),
            selectinload('sales_data')
        )
    
    @staticmethod
    def optimize_quotation_query(query: Query) -> Query:
        """
        优化报价单查询，预加载关联数据
        
        Args:
            query: 报价单查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('customer'),
            selectinload('items')
        )
    
    @staticmethod
    def optimize_sales_order_query(query: Query) -> Query:
        """
        优化销售订单查询，预加载关联数据
        
        Args:
            query: 销售订单查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('customer'),
            joinedload('quotation'),
            joinedload('material'),
            joinedload('production_version'),
            selectinload('contract_reviews')
        )
    
    @staticmethod
    def optimize_production_order_query(query: Query) -> Query:
        """
        优化生产订单查询，预加载关联数据
        
        Args:
            query: 生产订单查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('sales_order'),
            joinedload('material'),
            joinedload('production_version')
        )
    
    @staticmethod
    def optimize_bom_query(query: Query) -> Query:
        """
        优化BOM查询，预加载关联数据
        
        Args:
            query: BOM查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('parent_material'),
            selectinload('items').joinedload('material')
        )
    
    @staticmethod
    def optimize_routing_query(query: Query) -> Query:
        """
        优化工艺路线查询，预加载关联数据
        
        Args:
            query: 工艺路线查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('material'),
            selectinload('operations').joinedload('work_center')
        )
    
    @staticmethod
    def optimize_production_version_query(query: Query) -> Query:
        """
        优化生产版本查询，预加载关联数据
        
        Args:
            query: 生产版本查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('material'),
            joinedload('bom'),
            joinedload('routing'),
            joinedload('mi')
        )
    
    @staticmethod
    def optimize_operation_report_query(query: Query) -> Query:
        """
        优化工序报工查询，预加载关联数据
        
        Args:
            query: 工序报工查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('production_order'),
            joinedload('routing_operation'),
            joinedload('work_center')
        )
    
    @staticmethod
    def optimize_material_issue_query(query: Query) -> Query:
        """
        优化生产领料查询，预加载关联数据
        
        Args:
            query: 生产领料查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('production_order'),
            joinedload('material')
        )
    
    @staticmethod
    def optimize_factory_product_mapping_query(query: Query) -> Query:
        """
        优化本厂编号映射查询，预加载关联数据
        
        Args:
            query: 本厂编号映射查询对象
            
        Returns:
            优化后的查询对象
        """
        return query.options(
            joinedload('customer'),
            joinedload('material'),
            joinedload('production_version')
        )


def with_query_optimization(optimizer_method: str):
    """
    装饰器：为查询函数添加查询优化
    
    Args:
        optimizer_method: QueryOptimizer中的优化方法名
        
    Usage:
        @with_query_optimization('optimize_sales_order_query')
        async def list_sales_orders(query, ...):
            return query.all()
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 查找query参数
            query = None
            for arg in args:
                if isinstance(arg, Query):
                    query = arg
                    break
            
            if not query:
                query = kwargs.get('query')
            
            if query:
                # 应用优化
                optimizer = getattr(QueryOptimizer, optimizer_method)
                query = optimizer(query)
                
                # 更新参数
                if 'query' in kwargs:
                    kwargs['query'] = query
                else:
                    # 替换args中的query
                    args_list = list(args)
                    for i, arg in enumerate(args_list):
                        if isinstance(arg, Query):
                            args_list[i] = query
                            break
                    args = tuple(args_list)
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator

