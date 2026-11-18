#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从ER模型文档生成ECore模型文件
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

# 定义数据类型映射
TYPE_MAPPING = {
    'SERIAL': 'EInt',
    'INTEGER': 'EInt',
    'VARCHAR': 'EString',
    'TEXT': 'EString',
    'NUMERIC': 'EDouble',
    'DECIMAL': 'EDouble',
    'BOOLEAN': 'EBoolean',
    'DATE': 'EDate',
    'TIMESTAMP': 'EDate',
    'ENUM': 'EString',
    'JSON': 'EString',
}

# 定义所有实体及其属性
ENTITIES = {
    # 销售与分销模块 (SD Module)
    'Customer': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('customer_id', 'VARCHAR', True),
            ('legal_name', 'VARCHAR', True),
            ('trade_name', 'VARCHAR', False),
            ('tax_id', 'VARCHAR', False),
            ('customer_industry', 'VARCHAR', False),
            ('customer_website', 'VARCHAR', False),
            ('customer_status', 'ENUM', True),
            ('credit_limit', 'NUMERIC', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('addresses', 'CustomerAddress', True, False),
            ('contacts', 'CustomerContact', True, False),
            ('partnerFunctions', 'CustomerPartnerFunction', True, False),
            ('salesData', 'CustomerSalesData', True, False),
            ('quotations', 'Quotation', True, False),
            ('salesOrders', 'SalesOrder', True, False),
            ('factoryProductMappings', 'FactoryProductMapping', True, False),
        ]
    },
    'CustomerAddress': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('customer_id', 'VARCHAR', True),
            ('address_type', 'VARCHAR', True),
            ('detail_address', 'VARCHAR', True),
            ('location', 'VARCHAR', False),
            ('postal_code', 'VARCHAR', False),
            ('country', 'VARCHAR', False),
            ('province', 'VARCHAR', False),
            ('city', 'VARCHAR', False),
            ('district', 'VARCHAR', False),
            ('is_default_shipping', 'BOOLEAN', False),
            ('is_default_billing', 'BOOLEAN', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
        ]
    },
    'CustomerContact': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('customer_id', 'VARCHAR', True),
            ('is_primary_contact', 'BOOLEAN', False),
            ('contact_name', 'VARCHAR', True),
            ('contact_role', 'VARCHAR', False),
            ('contact_department', 'VARCHAR', False),
            ('contact_phone', 'VARCHAR', False),
            ('contact_email', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
        ]
    },
    'CustomerPartnerFunction': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('customer_id', 'VARCHAR', True),
            ('partner_function_type', 'VARCHAR', True),
            ('partner_start_date', 'DATE', False),
            ('partner_name', 'VARCHAR', False),
            ('partnership_description', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
        ]
    },
    'CustomerSalesData': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('customer_id', 'VARCHAR', True),
            ('sales_organization', 'VARCHAR', False),
            ('account_manager_name', 'VARCHAR', False),
            ('sales_assistant_name', 'VARCHAR', False),
            ('trading_currency', 'VARCHAR', False),
            ('primary_trade_country', 'VARCHAR', False),
            ('incoterms', 'VARCHAR', False),
            ('shipping_conditions', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
        ]
    },
    'FactoryProductMapping': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('customer_id', 'VARCHAR', True),
            ('factory_product_number', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('production_version_id', 'VARCHAR', False),
            ('is_default', 'BOOLEAN', False),
            ('effective_date', 'TIMESTAMP', True),
            ('expiry_date', 'TIMESTAMP', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
            ('material', 'Material', False, True),
            ('productionVersion', 'ProductionVersion', False, False),
        ]
    },
    'Quotation': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('quotation_number', 'VARCHAR', True),
            ('customer_id', 'VARCHAR', True),
            ('product_number', 'VARCHAR', False),
            ('quantity', 'NUMERIC', False),
            ('unit_price', 'NUMERIC', False),
            ('total_amount', 'NUMERIC', False),
            ('currency', 'VARCHAR', False),
            ('valid_until', 'DATE', False),
            ('status', 'ENUM', True),
            ('sales_approver', 'VARCHAR', False),
            ('sales_approved_at', 'TIMESTAMP', False),
            ('finance_approver', 'VARCHAR', False),
            ('finance_approved_at', 'TIMESTAMP', False),
            ('general_manager_approver', 'VARCHAR', False),
            ('general_manager_approved_at', 'TIMESTAMP', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
            ('items', 'QuotationItem', True, False),
            ('salesOrders', 'SalesOrder', True, False),
        ]
    },
    'QuotationItem': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('quotation_number', 'VARCHAR', True),
            ('line_number', 'INTEGER', True),
            ('material_code', 'VARCHAR', False),
            ('material_name', 'VARCHAR', False),
            ('quantity', 'NUMERIC', False),
            ('unit_price', 'NUMERIC', False),
            ('total_price', 'NUMERIC', False),
            ('remarks', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('quotation', 'Quotation', False, True),
        ]
    },
    'SalesOrder': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('order_number', 'VARCHAR', True),
            ('quotation_number', 'VARCHAR', False),
            ('customer_id', 'VARCHAR', True),
            ('product_number', 'VARCHAR', False),
            ('material_code', 'VARCHAR', False),
            ('production_version_id', 'VARCHAR', False),
            ('quantity', 'NUMERIC', True),
            ('sales_unit', 'VARCHAR', False),
            ('production_quantity', 'NUMERIC', False),
            ('production_unit', 'VARCHAR', False),
            ('conversion_factor', 'NUMERIC', False),
            ('delivery_date', 'DATE', False),
            ('status', 'ENUM', True),
            ('is_return_order', 'BOOLEAN', False),
            ('review_status', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('customer', 'Customer', False, True),
            ('quotation', 'Quotation', False, False),
            ('material', 'Material', False, False),
            ('productionVersion', 'ProductionVersion', False, False),
            ('contractReviews', 'ContractReview', True, False),
            ('productionOrders', 'ProductionOrder', True, False),
        ]
    },
    'ContractReview': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('sales_order_number', 'VARCHAR', True),
            ('reviewer_role', 'VARCHAR', True),
            ('reviewer', 'VARCHAR', True),
            ('review_result', 'VARCHAR', True),
            ('review_comment', 'TEXT', False),
            ('reviewed_at', 'TIMESTAMP', True),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('salesOrder', 'SalesOrder', False, True),
        ]
    },
    
    # 工程管理模块 (ENG Module)
    'Material': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('material_code', 'VARCHAR', True),
            ('material_name', 'VARCHAR', True),
            ('material_type', 'VARCHAR', True),
            ('status', 'VARCHAR', False),
            ('base_unit', 'VARCHAR', True),
            ('production_unit', 'VARCHAR', False),
            ('conversion_factor', 'NUMERIC', False),
            ('current_stock', 'NUMERIC', False),
            ('safety_stock', 'NUMERIC', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('boms', 'BOM', True, False),
            ('bomItems', 'BOMItem', True, False),
            ('routings', 'Routing', True, False),
            ('mis', 'MI', True, False),
            ('productionVersions', 'ProductionVersion', True, False),
            ('materialIssues', 'MaterialIssue', True, False),
            ('materialTransactions', 'MaterialTransaction', True, False),
            ('salesOrders', 'SalesOrder', True, False),
            ('productionOrders', 'ProductionOrder', True, False),
            ('factoryProductMappings', 'FactoryProductMapping', True, False),
        ]
    },
    'BOM': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('bom_number', 'VARCHAR', True),
            ('version', 'VARCHAR', True),
            ('parent_material_code', 'VARCHAR', True),
            ('base_quantity', 'NUMERIC', False),
            ('base_uom', 'VARCHAR', False),
            ('status', 'ENUM', True),
            ('effective_date', 'DATE', True),
            ('expiry_date', 'DATE', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('parentMaterial', 'Material', False, True),
            ('items', 'BOMItem', True, False),
            ('productionVersions', 'ProductionVersion', True, False),
        ]
    },
    'BOMItem': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('bom_number', 'VARCHAR', True),
            ('line_number', 'INTEGER', True),
            ('material_code', 'VARCHAR', True),
            ('item_category', 'VARCHAR', False),
            ('quantity', 'NUMERIC', True),
            ('unit', 'VARCHAR', True),
            ('scrap_rate', 'NUMERIC', False),
            ('layer_code', 'VARCHAR', False),
            ('material_type', 'VARCHAR', False),
            ('process_step', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('bom', 'BOM', False, True),
            ('material', 'Material', False, True),
        ]
    },
    'Routing': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('routing_id', 'VARCHAR', True),
            ('version', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('base_unit', 'VARCHAR', False),
            ('base_quantity', 'NUMERIC', False),
            ('units_per_panel', 'INTEGER', False),
            ('panel_size', 'VARCHAR', False),
            ('status', 'ENUM', True),
            ('effective_date', 'DATE', True),
            ('expiry_date', 'DATE', False),
            ('change_request_no', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('material', 'Material', False, True),
            ('operations', 'RoutingOperation', True, False),
            ('productionVersions', 'ProductionVersion', True, False),
        ]
    },
    'RoutingOperation': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('routing_id', 'VARCHAR', True),
            ('operation_no', 'VARCHAR', True),
            ('operation_code', 'VARCHAR', True),
            ('operation_name', 'VARCHAR', True),
            ('operation_type', 'VARCHAR', True),
            ('work_center_id', 'VARCHAR', True),
            ('sop_link', 'VARCHAR', False),
            ('setup_time', 'NUMERIC', False),
            ('machine_time', 'NUMERIC', False),
            ('labor_time', 'NUMERIC', False),
            ('queue_time', 'NUMERIC', False),
            ('cost_relevant', 'BOOLEAN', False),
            ('scheduling_relevant', 'BOOLEAN', False),
            ('needs_reporting', 'BOOLEAN', False),
            ('auto_deduct_material', 'BOOLEAN', False),
            ('trigger_quality_check', 'BOOLEAN', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('routing', 'Routing', False, True),
            ('workCenter', 'WorkCenter', False, True),
            ('operationReports', 'OperationReport', True, False),
        ]
    },
    'MI': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('mi_number', 'VARCHAR', True),
            ('version', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('description', 'VARCHAR', False),
            ('status', 'ENUM', True),
            ('effective_date', 'DATE', True),
            ('expiry_date', 'DATE', False),
            ('content', 'TEXT', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('material', 'Material', False, True),
            ('productionVersions', 'ProductionVersion', True, False),
        ]
    },
    'ProductionVersion': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('production_version_id', 'VARCHAR', True),
            ('version', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('bom_number', 'VARCHAR', True),
            ('routing_id', 'VARCHAR', True),
            ('mi_number', 'VARCHAR', False),
            ('status', 'VARCHAR', False),
            ('effective_date', 'DATE', True),
            ('expiry_date', 'DATE', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('material', 'Material', False, True),
            ('bom', 'BOM', False, True),
            ('routing', 'Routing', False, True),
            ('mi', 'MI', False, False),
            ('salesOrders', 'SalesOrder', True, False),
            ('productionOrders', 'ProductionOrder', True, False),
            ('factoryProductMappings', 'FactoryProductMapping', True, False),
        ]
    },
    
    # 物料管理模块 (MM Module)
    'MaterialIssue': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('issue_number', 'VARCHAR', True),
            ('production_order_number', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('quantity', 'NUMERIC', True),
            ('unit', 'VARCHAR', True),
            ('warehouse', 'VARCHAR', False),
            ('issued_by', 'VARCHAR', False),
            ('issued_at', 'TIMESTAMP', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('productionOrder', 'ProductionOrder', False, True),
            ('material', 'Material', False, True),
        ]
    },
    'MaterialTransaction': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('transaction_number', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('transaction_type', 'VARCHAR', True),
            ('quantity', 'NUMERIC', True),
            ('unit', 'VARCHAR', True),
            ('reference_number', 'VARCHAR', False),
            ('reference_type', 'VARCHAR', False),
            ('transaction_date', 'TIMESTAMP', False),
            ('operator', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('material', 'Material', False, True),
        ]
    },
    
    # 生产计划与控制模块 (PP Module)
    'WorkCenter': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('work_center_id', 'VARCHAR', True),
            ('description', 'VARCHAR', False),
            ('work_center_type', 'VARCHAR', True),
            ('plant_id', 'VARCHAR', False),
            ('status', 'ENUM', True),
            ('parent_work_center_id', 'VARCHAR', False),
            ('hierarchy_level', 'INTEGER', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('parent', 'WorkCenter', False, False),
            ('children', 'WorkCenter', True, False),
            ('routingOperations', 'RoutingOperation', True, False),
            ('operationReports', 'OperationReport', True, False),
        ]
    },
    'ProductionOrder': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('order_number', 'VARCHAR', True),
            ('sales_order_number', 'VARCHAR', True),
            ('material_code', 'VARCHAR', True),
            ('production_version_id', 'VARCHAR', False),
            ('quantity', 'NUMERIC', True),
            ('unit', 'VARCHAR', True),
            ('sales_quantity', 'NUMERIC', False),
            ('sales_unit', 'VARCHAR', False),
            ('conversion_factor', 'NUMERIC', False),
            ('planned_start_date', 'DATE', False),
            ('planned_finish_date', 'DATE', False),
            ('actual_start_date', 'DATE', False),
            ('actual_finish_date', 'DATE', False),
            ('status', 'ENUM', True),
            ('lot_number', 'VARCHAR', False),
            ('remarks', 'TEXT', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('salesOrder', 'SalesOrder', False, True),
            ('material', 'Material', False, True),
            ('productionVersion', 'ProductionVersion', False, False),
            ('materialIssues', 'MaterialIssue', True, False),
            ('operationReports', 'OperationReport', True, False),
        ]
    },
    'OperationReport': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('report_number', 'VARCHAR', True),
            ('production_order_number', 'VARCHAR', True),
            ('routing_operation_id', 'INTEGER', False),
            ('work_center_id', 'VARCHAR', True),
            ('operation_no', 'VARCHAR', True),
            ('operation_name', 'VARCHAR', False),
            ('reported_quantity', 'NUMERIC', True),
            ('good_quantity', 'NUMERIC', True),
            ('scrap_quantity', 'NUMERIC', False),
            ('setup_time', 'NUMERIC', False),
            ('machine_time', 'NUMERIC', False),
            ('labor_time', 'NUMERIC', False),
            ('reported_by', 'VARCHAR', False),
            ('reported_at', 'TIMESTAMP', False),
            ('status', 'ENUM', True),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('productionOrder', 'ProductionOrder', False, True),
            ('routingOperation', 'RoutingOperation', False, False),
            ('workCenter', 'WorkCenter', False, True),
        ]
    },
    
    # 用户与权限管理模块
    'User': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('username', 'VARCHAR', True),
            ('email', 'VARCHAR', True),
            ('password_hash', 'VARCHAR', True),
            ('full_name', 'VARCHAR', False),
            ('role', 'ENUM', True),
            ('department', 'VARCHAR', False),
            ('is_active', 'BOOLEAN', True),
            ('phone', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': []
    },
    
    # 工作流模块
    'Workflow': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('workflow_id', 'VARCHAR', True),
            ('workflow_name', 'VARCHAR', True),
            ('module', 'VARCHAR', False),
            ('description', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('nodes', 'WorkflowNode', True, False),
            ('instances', 'WorkflowInstance', True, False),
        ]
    },
    'WorkflowNode': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('workflow_id', 'VARCHAR', True),
            ('node_id', 'VARCHAR', True),
            ('node_name', 'VARCHAR', True),
            ('node_type', 'VARCHAR', True),
            ('approver_role', 'VARCHAR', False),
            ('order', 'INTEGER', True),
            ('config', 'JSON', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('workflow', 'Workflow', False, True),
        ]
    },
    'WorkflowInstance': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('instance_id', 'VARCHAR', True),
            ('workflow_id', 'VARCHAR', True),
            ('business_id', 'VARCHAR', True),
            ('business_type', 'VARCHAR', True),
            ('status', 'ENUM', True),
            ('current_node_id', 'VARCHAR', False),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('completed_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('workflow', 'Workflow', False, True),
            ('nodes', 'WorkflowInstanceNode', True, False),
        ]
    },
    'WorkflowInstanceNode': {
        'attributes': [
            ('id', 'SERIAL', True),
            ('instance_id', 'VARCHAR', True),
            ('node_id', 'VARCHAR', True),
            ('status', 'ENUM', True),
            ('approver', 'VARCHAR', False),
            ('approved_at', 'TIMESTAMP', False),
            ('comment', 'VARCHAR', False),
            ('order', 'INTEGER', True),
            ('created_by', 'VARCHAR', False),
            ('created_at', 'TIMESTAMP', False),
            ('updated_by', 'VARCHAR', False),
            ('updated_at', 'TIMESTAMP', False),
            ('is_deleted', 'BOOLEAN', True),
        ],
        'references': [
            ('instance', 'WorkflowInstance', False, True),
        ]
    },
}


def get_ecore_type(db_type):
    """将数据库类型转换为ECore类型"""
    for key, value in TYPE_MAPPING.items():
        if key in db_type.upper():
            return value
    return 'EString'  # 默认类型


def create_ecore_file():
    """创建ECore模型文件"""
    # 创建根元素
    root = ET.Element('ecore:EPackage', {
        'xmlns:ecore': 'http://www.eclipse.org/emf/2002/Ecore',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsi:schemaLocation': 'http://www.eclipse.org/emf/2002/Ecore http://www.eclipse.org/emf/2002/Ecore.xsd',
        'nsURI': 'http://www.hserp.com/model',
        'nsPrefix': 'hserp',
        'name': 'HSERPModel'
    })
    
    # 创建所有EClass
    for class_name, class_info in ENTITIES.items():
        eclass = ET.SubElement(root, 'eClassifiers', {
            'xsi:type': 'ecore:EClass',
            'name': class_name
        })
        
        # 添加属性
        for attr_name, attr_type, is_required in class_info['attributes']:
            eattr = ET.SubElement(eclass, 'eStructuralFeatures', {
                'xsi:type': 'ecore:EAttribute',
                'name': attr_name,
                'eType': f'ecore:EDataType http://www.eclipse.org/emf/2002/Ecore#//{get_ecore_type(attr_type)}',
                'lowerBound': '1' if is_required else '0',
                'upperBound': '1'
            })
        
        # 添加引用关系
        for ref_name, ref_type, is_many, is_required in class_info['references']:
            eref = ET.SubElement(eclass, 'eStructuralFeatures', {
                'xsi:type': 'ecore:EReference',
                'name': ref_name,
                'eType': f'#//{ref_type}',
                'lowerBound': '1' if is_required else '0',
                'upperBound': '-1' if is_many else '1',
                'containment': 'true' if is_many else 'false'
            })
            
            # 设置反向引用
            if is_many:
                eref.set('eOpposite', f'#//{ref_type}/{ref_name.replace("s", "") if ref_name.endswith("s") else ref_name}')
    
    # 格式化XML
    xml_str = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='utf-8')
    
    return pretty_xml


def main():
    """主函数"""
    ecore_xml = create_ecore_file()
    
    # 写入文件
    output_file = '某某ERP系统 - ECore模型.ecore'
    with open(output_file, 'wb') as f:
        f.write(ecore_xml)
    
    print(f'ECore模型文件已生成: {output_file}')
    print(f'包含 {len(ENTITIES)} 个实体类')


if __name__ == '__main__':
    main()

