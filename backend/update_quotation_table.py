"""
更新报价单表结构，添加新字段
"""
import os
import sys
from pathlib import Path

# 设置UTF-8编码（Windows控制台）
if sys.platform == 'win32':
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except:
        pass

# 添加项目根目录到Python路径
script_dir = Path(__file__).parent
project_root = script_dir.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text, inspect
from backend.common.database.base import engine, DATABASE_URL

def update_quotation_table():
    """更新报价单表，添加新字段"""
    print("=" * 50)
    print("更新报价单表结构")
    print("=" * 50)
    print()
    
    # 新字段列表（字段名: SQL类型）
    new_fields = {
        # 报价明细 - 板规格参数
        'utilization_rate': 'NUMERIC(10, 4)',
        'delivery_length': 'NUMERIC(10, 2)',
        'delivery_width': 'NUMERIC(10, 2)',
        'set_per_unit': 'INTEGER DEFAULT 1',
        'material_type': 'VARCHAR(50)',
        'tg_value': 'VARCHAR(50)',
        'finished_board_thickness': 'VARCHAR(50)',
        'large_material_spec': 'VARCHAR(50)',
        'large_material_pnl_count': 'INTEGER',
        'pnl_set_count': 'INTEGER',
        'pnl_length_mm': 'NUMERIC(10, 2)',
        'pnl_width_mm': 'NUMERIC(10, 2)',
        'core_board_count': 'INTEGER',
        'core_board_spec': 'VARCHAR(200)',
        'inner_layer_thickening': 'BOOLEAN DEFAULT FALSE',
        'outer_line_width_spacing_limit': 'BOOLEAN DEFAULT FALSE',
        'solder_mask_color_detail': 'VARCHAR(50)',
        'times': 'INTEGER DEFAULT 1',
        'specify_sun': 'BOOLEAN DEFAULT FALSE',
        'board_thickness_tolerance': 'BOOLEAN DEFAULT FALSE',
        'via_plugging': 'VARCHAR(50)',
        'character_color_detail': 'VARCHAR(50)',
        'min_drill_bit': 'VARCHAR(50)',
        'set_hole_count': 'INTEGER',
        'pcs_conversion': 'NUMERIC(10, 2)',
        'pnl_conversion': 'NUMERIC(10, 2)',
        'acceptance_standard': 'VARCHAR(50)',
        'routing_process': 'NUMERIC(10, 2)',
        'v_score_process': 'NUMERIC(10, 2)',
        'hard_gold': 'BOOLEAN DEFAULT FALSE',
        'no_positioning_hole_routing': 'BOOLEAN DEFAULT FALSE',
        'test_points': 'INTEGER DEFAULT 0',
        # 报价明细 - 加价选项
        'regular_surcharges': 'JSON',
        'special_surcharges': 'JSON',
        'additional_surcharge_per_m2': 'NUMERIC(15, 2)',
        'customer_provides_hf_board': 'BOOLEAN DEFAULT FALSE',
        'min_customer_consumption': 'NUMERIC(15, 2)',
        'market_quote_remarks': 'VARCHAR(500)',
        # 报价明细 - 计算结果
        'actual_p_input': 'INTEGER',
        'delivery_area': 'NUMERIC(15, 4)',
        'cost_per_pcs': 'NUMERIC(15, 4)',
        'cost_per_m2': 'NUMERIC(15, 4)',
        'quote_price_per_pcs': 'NUMERIC(15, 4)',
        'quote_price_per_m2': 'NUMERIC(15, 4)',
        'test_fixture': 'NUMERIC(15, 2)',
        'other_costs': 'NUMERIC(15, 2)',
        'final_total_price': 'NUMERIC(15, 2)',
    }
    
    try:
        inspector = inspect(engine)
        existing_columns = [col['name'] for col in inspector.get_columns('quotations')]
        
        print(f"现有字段数: {len(existing_columns)}")
        print(f"需要添加的字段数: {len(new_fields)}")
        print()
        
        added_count = 0
        with engine.connect() as conn:
            for field_name, field_type in new_fields.items():
                if field_name not in existing_columns:
                    try:
                        sql = f"ALTER TABLE quotations ADD COLUMN {field_name} {field_type};"
                        print(f"添加字段: {field_name} ({field_type})")
                        conn.execute(text(sql))
                        conn.commit()
                        added_count += 1
                    except Exception as e:
                        print(f"  错误: 添加字段 {field_name} 失败: {e}")
                        conn.rollback()
                else:
                    print(f"字段已存在: {field_name}")
        
        print()
        print(f"成功添加 {added_count} 个新字段")
        print("=" * 50)
        print("更新完成！")
        print("=" * 50)
        
    except Exception as e:
        print(f"[ERROR] 更新失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    update_quotation_table()
