import { Form, Input, Select, Button, Card, Row, Col, Space, App as AntdApp, DatePicker, InputNumber, Collapse, Divider, Checkbox, Switch, Tabs, Table } from 'antd'
import { useNavigate, useParams } from 'react-router-dom'
import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import api from '../../services/api'

const { Option } = Select
const { TextArea } = Input

const QuotationForm: React.FC = () => {
  const { message } = AntdApp.useApp()
  const [form] = Form.useForm()
  const navigate = useNavigate()
  const { id } = useParams<{ id?: string }>()
  const [loading, setLoading] = useState(false)
  const [customers, setCustomers] = useState<any[]>([])
  const [priceDetails, setPriceDetails] = useState({
    engineering_fee: 0,
    board_material_fee_amount: 0,
    via_fee: 0,
    estimated_total_price: 0
  })
  const [quotationNumber, setQuotationNumber] = useState<string>('')
  const [calculationResult, setCalculationResult] = useState<any>(null)
  const [processDetails, setProcessDetails] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<string>('basic')
  const [, setSelectedProduct] = useState<any>(null)
  const isEdit = !!id

  // 同步报价明细字段到基本信息
  const syncDetailsToBasic = (fieldName: string, value: any) => {
    const syncFields: any = {}
    
    // 字段映射：报价明细 → 基本信息
    switch (fieldName) {
      case 'delivery_length':
        // mm转cm
        if (value !== undefined && value !== null) {
          syncFields.single_piece_length = value / 10
        }
        break
      case 'delivery_width':
        // mm转cm
        if (value !== undefined && value !== null) {
          syncFields.single_piece_width = value / 10
        }
        break
      case 'material_type': {
        // 板材类型映射到产品类别
        const categoryMap: any = {
          'FR4': 'FR-4',
          '高频板': '罗杰斯高频板'
        }
        if (value) {
          syncFields.product_category = categoryMap[value] || value
        }
        break
      }
      case 'tg_value':
        syncFields.board_material_tg = value
        break
      case 'finished_board_thickness':
        syncFields.board_thickness = value
        break
      case 'solder_mask_color_detail':
        syncFields.solder_mask_color = value
        break
      case 'character_color_detail':
        syncFields.character_color = value
        break
      case 'outer_copper_thickness':
        // 1OZ转换为1oz格式
        if (value) {
          const copperMap: any = {
            '1OZ': '1oz',
            '2OZ': '2oz',
            '3OZ': '3oz',
            '4OZ': '4oz'
          }
          syncFields.outer_copper_thickness = copperMap[value] || value
        }
        break
      case 'surface_finish':
        syncFields.surface_finish = value
        break
      case 'inner_copper_thickness':
        syncFields.inner_copper_thickness = value
        break
      case 'layers':
        syncFields.layers = value
        break
      case 'min_drill_bit':
        syncFields.min_hole_diameter = value
        break
      case 'via_plugging':
        // 过孔塞孔映射到阻焊覆盖
        if (value === '阻焊塞孔') {
          syncFields.solder_mask_coverage = '过孔塞油墨'
        } else if (value === '树脂塞孔') {
          syncFields.solder_mask_coverage = '过孔塞树脂+电镀填平'
        }
        break
    }
    
    // 更新基本信息字段
    if (Object.keys(syncFields).length > 0) {
      form.setFieldsValue(syncFields)
    }
  }

  // 当切换到报价明细标签页时，自动从基本信息同步字段
  const handleTabChange = (key: string) => {
    setActiveTab(key)
    if (key === 'details') {
      // 切换到报价明细标签页时，自动同步基本信息中的字段
      const values = form.getFieldsValue()
      const syncFields: any = {}
      
      // 同步尺寸信息（如果报价明细中没有值）
      if (!values.delivery_length && values.single_piece_length) {
        syncFields.delivery_length = values.single_piece_length * 10 // cm转mm
      }
      if (!values.delivery_width && values.single_piece_width) {
        syncFields.delivery_width = values.single_piece_width * 10 // cm转mm
      }
      
      // 同步板材信息
      if (!values.material_type && values.product_category) {
        // 产品类别映射到板材类型
        const categoryMap: any = {
          'FR-4': 'FR4',
          '罗杰斯高频板': '高频板'
        }
        syncFields.material_type = categoryMap[values.product_category] || values.product_category
      }
      if (!values.tg_value && values.board_material_tg) {
        syncFields.tg_value = values.board_material_tg
      }
      
      // 同步工艺信息
      if (!values.finished_board_thickness && values.board_thickness) {
        syncFields.finished_board_thickness = values.board_thickness
      }
      if (!values.solder_mask_color_detail && values.solder_mask_color) {
        syncFields.solder_mask_color_detail = values.solder_mask_color
      }
      if (!values.character_color_detail && values.character_color) {
        syncFields.character_color_detail = values.character_color
      }
      if (!values.outer_copper_thickness) {
        // 将1oz转换为1OZ格式
        const copperMap: any = {
          '1oz': '1OZ',
          '2oz': '2OZ',
          '3oz': '3OZ',
          '4oz': '4OZ'
        }
        if (values.outer_copper_thickness) {
          syncFields.outer_copper_thickness = copperMap[values.outer_copper_thickness] || values.outer_copper_thickness
        }
      }
      
      // 如果有需要同步的字段，更新表单
      if (Object.keys(syncFields).length > 0) {
        form.setFieldsValue(syncFields)
      }
    }
  }

  useEffect(() => {
    fetchCustomers()
    if (isEdit) {
      fetchQuotation()
    } else {
      // 新建时初始化价格计算
      setTimeout(() => {
        const values = form.getFieldsValue()
        calculatePrice(values)
      }, 100)
    }
  }, [id])

  const fetchCustomers = async () => {
    try {
      // 只获取已激活的客户
      const response = await api.get('/sd/customers', {
        params: {
          status: 'ACTIVE'
        }
      })
      setCustomers(response.data)
    } catch (error) {
      console.error('获取客户列表失败:', error)
    }
  }

  // 计算价格明细
  const calculatePrice = (values: any) => {
    // 这里可以根据实际业务规则计算各项费用
    // 目前使用简单的示例计算逻辑，实际应该根据产品配置、工艺信息等计算
    let engineeringFee = 150 // 默认工程费
    let boardMaterialFee = 31 // 默认板材费
    let viaFee = 84 // 默认过孔费
    
    // 根据层数调整工程费
    if (values.layers) {
      if (values.layers <= 2) {
        engineeringFee = 100
      } else if (values.layers <= 4) {
        engineeringFee = 150
      } else if (values.layers <= 6) {
        engineeringFee = 200
      } else {
        engineeringFee = 250
      }
    }
    
    // 根据板材品牌调整板材费
    if (values.board_material_brand) {
      if (values.board_material_brand.includes('建滔')) {
        boardMaterialFee = 31
      } else if (values.board_material_brand.includes('生益')) {
        boardMaterialFee = 35
      }
    }
    
    // 根据HDI类型调整过孔费
    if (values.hdi_type) {
      if (values.hdi_type === '无') {
        viaFee = 84
      } else if (values.hdi_type === '1阶') {
        viaFee = 120
      } else if (values.hdi_type === '2阶') {
        viaFee = 180
      } else if (values.hdi_type === '3阶') {
        viaFee = 250
      }
    }
    
    const estimatedTotal = engineeringFee + boardMaterialFee + viaFee
    
    setPriceDetails({
      engineering_fee: engineeringFee,
      board_material_fee_amount: boardMaterialFee,
      via_fee: viaFee,
      estimated_total_price: estimatedTotal
    })
    
    // 更新表单中的预估总价字段
    form.setFieldsValue({
      engineering_fee: engineeringFee,
      board_material_fee_amount: boardMaterialFee,
      via_fee: viaFee,
      estimated_total_price: estimatedTotal,
      unit_price: estimatedTotal // 保持unit_price字段用于后端兼容
    })
  }

  const fetchQuotation = async () => {
    try {
      const response = await api.get(`/sd/quotations/${id}`)
      const data = response.data
      
      // 设置报价单编号
      setQuotationNumber(data.quotation_number)
      
      // 展开个性化服务JSON字段
      const personalizedServices = data.personalized_services || {}
      
      // 合并数量字段：如果single_piece_quantity不存在，使用quantity
      const singlePieceQuantity = data.single_piece_quantity !== undefined && data.single_piece_quantity !== null 
        ? data.single_piece_quantity 
        : data.quantity
      
      // 设置价格明细
      if (data.engineering_fee || data.board_material_fee_amount || data.via_fee || data.estimated_total_price) {
        setPriceDetails({
          engineering_fee: data.engineering_fee || 0,
          board_material_fee_amount: data.board_material_fee_amount || 0,
          via_fee: data.via_fee || 0,
          estimated_total_price: data.estimated_total_price || data.unit_price || 0
        })
      } else {
        // 如果没有价格明细，使用unit_price作为预估总价
        setPriceDetails({
          engineering_fee: 0,
          board_material_fee_amount: 0,
          via_fee: 0,
          estimated_total_price: data.unit_price || 0
        })
      }
      
      const formValues: any = {
        ...data,
        valid_until: data.valid_until ? dayjs(data.valid_until) : undefined,
        // 合并数量字段
        single_piece_quantity: singlePieceQuantity,
        // 价格明细
        engineering_fee: data.engineering_fee,
        board_material_fee_amount: data.board_material_fee_amount,
        via_fee: data.via_fee,
        estimated_total_price: data.estimated_total_price || data.unit_price,
        // 展开个性化服务字段
        production_draft_confirmation: personalizedServices['确认生产稿'] || '无需',
        huaqiu_logo_cycle: personalizedServices['华秋标识和制造周期'] || '无需',
        cycle_format: personalizedServices['周期格式'] || '周/年',
        customer_code: personalizedServices['客编'] || '不加客编',
        accept_scoring_board: personalizedServices['打叉板'] === '接受打叉板',
        eq_confirmation_method: personalizedServices['工程EQ确认方式'] || '平台推送',
        minority_handling: personalizedServices['少数处理方式'] || '不设置',
        quality_compensation: personalizedServices['品质赔付方式'] || '标准赔付',
        shipping_report: personalizedServices['产品报告']?.出货报告 || false,
        slice_report: personalizedServices['产品报告']?.切片报告 || false,
        physical_film: personalizedServices['产品报告']?.实物菲林 || false,
        white_paper_isolation: personalizedServices['隔白纸'] || '无需',
        inner_label: personalizedServices['内标签'] || '无需',
        inner_label_remark: personalizedServices['内包装标签备注'] || '',
        carton_requirement: personalizedServices['纸箱要求'] || '华秋标识纸箱',
        audit_notification: personalizedServices['审核通知'] || '无需'
      }
      
      form.setFieldsValue(formValues)
      
      // 如果报价单中有本厂编号，自动加载产品名称
      if (data.product_number) {
        try {
          const materialResponse = await api.get(`/mm/materials/${data.product_number}`)
          const material = materialResponse.data
          if (material) {
            setSelectedProduct(material)
            form.setFieldsValue({ product_name: material.material_name || data.product_name })
          }
        } catch (error) {
          // 产品不存在，使用报价单中已有的产品名称（如果有）
          if (data.product_name) {
            form.setFieldsValue({ product_name: data.product_name })
          }
        }
      }
      
      // 设置表单值后，重新计算价格（如果字段有变化）
      setTimeout(() => {
        const currentValues = form.getFieldsValue()
        calculatePrice(currentValues)
      }, 100)
    } catch (error) {
      message.error('获取报价单信息失败')
      navigate('/sd/quotations')
    }
  }

  // 计算报价明细成本
  const calculateQuotationDetails = async () => {
    try {
      const values = form.getFieldsValue()
      
      // 自动从基本信息标签页读取字段，优先使用报价明细中的值，如果没有则使用基本信息的值
      const calculationData: any = {
        // 层数（从基本信息板材信息中读取）
        layers: values.layers || undefined,
        
        // 尺寸信息（优先使用报价明细中的值，如果没有则使用基本信息中的值）
        utilization_rate: values.utilization_rate || undefined,
        delivery_length: values.delivery_length || (values.single_piece_length ? values.single_piece_length * 10 : undefined), // cm转mm
        delivery_width: values.delivery_width || (values.single_piece_width ? values.single_piece_width * 10 : undefined), // cm转mm
        set_per_unit: values.set_per_unit || 1,
        
        // 板材信息（从基本信息中读取）
        material_type: values.material_type || (values.product_category === 'FR-4' ? 'FR4' : values.product_category === '罗杰斯高频板' ? '高频板' : values.product_category) || undefined,
        tg_value: values.tg_value || values.board_material_tg || undefined,
        
        // 板厚（从工艺信息中读取）
        finished_board_thickness: values.finished_board_thickness || values.board_thickness || undefined,
        
        // 铜厚信息（从工艺信息中读取）
        outer_copper_thickness: values.outer_copper_thickness || undefined,
        inner_copper_thickness: values.inner_copper_thickness || undefined,
        inner_layer_thickening: values.inner_layer_thickening || false,
        outer_line_width_spacing_limit: values.outer_line_width_spacing_limit || false,
        
        // 表面处理和颜色（从工艺信息中读取）
        surface_finish: values.surface_finish || undefined,
        solder_mask_color_detail: values.solder_mask_color_detail || values.solder_mask_color || undefined,
        character_color_detail: values.character_color_detail || values.character_color || undefined,
        
        // 工艺参数（从工艺信息中读取）
        times: values.times || 1,
        specify_sun: values.specify_sun || false,
        board_thickness_tolerance: values.board_thickness_tolerance || false,
        via_plugging: values.via_plugging || (values.solder_mask_coverage === '过孔塞油墨' ? '阻焊塞孔' : values.solder_mask_coverage === '过孔塞树脂+电镀填平' ? '树脂塞孔' : undefined),
        min_drill_bit: values.min_drill_bit || values.min_hole_diameter || undefined,
        set_hole_count: values.set_hole_count || undefined,
        acceptance_standard: values.acceptance_standard || undefined,
        routing_process: values.routing_process || undefined,
        v_score_process: values.v_score_process || undefined,
        hard_gold: values.hard_gold || false,
        no_positioning_hole_routing: values.no_positioning_hole_routing || false,
        test_points: values.test_points || 0,
        
        // 报价明细特有字段（如果报价明细中没有，则不传递）
        large_material_spec: values.large_material_spec || undefined,
        large_material_pnl_count: values.large_material_pnl_count || undefined,
        pnl_set_count: values.pnl_set_count || undefined,
        pnl_length_mm: values.pnl_length_mm || undefined,
        pnl_width_mm: values.pnl_width_mm || undefined,
        core_board_count: values.core_board_count || undefined,
        core_board_spec: values.core_board_spec || undefined,
        pcs_conversion: values.pcs_conversion || undefined,
        pnl_conversion: values.pnl_conversion || undefined,
        
        // 加价选项
        regular_surcharges: values.regular_surcharges || {},
        special_surcharges: values.special_surcharges || {},
        additional_surcharge_per_m2: values.additional_surcharge_per_m2 || undefined,
        customer_provides_hf_board: values.customer_provides_hf_board || false,
        min_customer_consumption: values.min_customer_consumption || undefined,
        market_quote_remarks: values.market_quote_remarks || undefined,
        
        // 订单数量（从基本信息中读取）
        order_quantity: values.single_piece_quantity || values.quantity || 1
      }
      
      // 移除undefined值，避免传递空值
      Object.keys(calculationData).forEach(key => {
        if (calculationData[key] === undefined) {
          delete calculationData[key]
        }
      })
      
      // 已保存报价单 → 明细重算；未保存（新建/草稿）→ 试算（preview，不写库）
      let response
      if (quotationNumber) {
        response = await api.post(`/sd/quotations/${quotationNumber}/calculate-details`, calculationData)
      } else {
        response = await api.post('/sd/quotations/preview-details', calculationData)
      }
      
      setCalculationResult(response.data)
      setProcessDetails(response.data.process_details || [])
      
      // 更新价格明细状态，用于提交时使用
      setPriceDetails({
        engineering_fee: response.data.engineering_fee || 0,
        board_material_fee_amount: response.data.board_material_fee || 0,
        via_fee: 0,
        estimated_total_price: response.data.final_total_price || 0
      })
      
      message.success('成本计算完成')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '成本计算失败'
      message.error(errorMsg)
      console.error('成本计算失败:', error)
    }
  }

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      // 新建报价单时，检查14位本厂编号是否存在对应的产品主数据
      if (!isEdit && values.product_number) {
        const productNumber = values.product_number.trim()
        
        // 检查本厂编号是否为14位
        if (productNumber.length === 14) {
          try {
            // 检查物料是否存在（使用本厂编号作为material_code）
            try {
              await api.get(`/mm/materials/${productNumber}`)
              // 物料存在，继续检查产品主数据映射
            } catch (materialError: any) {
              // 物料不存在，需要创建物料和产品主数据
              if (materialError.response?.status === 404) {
                // 从报价单信息中提取产品信息，生成产品名称
                // 优先使用产品编号作为名称，如果没有则使用本厂编号
                const materialName = productNumber || `产品-${productNumber}`
                
                // 创建物料主数据（产品）
                const materialData = {
                  material_code: productNumber,
                  material_name: materialName,
                  material_type: 'FG',
                  category: '成品',
                  unit: 'PCS',
                  current_stock: 0,
                  safety_stock: 0,
                  status: 'ACTIVE',
                  base_unit: 'PCS',
                  production_unit: 'PCS',
                  conversion_factor: 1,
                  // 从报价单中提取PCB相关属性
                  layer_count: values.layers || undefined,
                  board_thickness: values.finished_board_thickness || values.board_thickness ? parseFloat(values.finished_board_thickness || values.board_thickness) : undefined,
                  surface_finish: values.surface_finish || undefined,
                  solder_mask_color: values.solder_mask_color_detail || values.solder_mask_color || undefined,
                  silkscreen_color: values.character_color_detail || values.character_color || undefined,
                  // 尺寸信息
                  unit_length: values.delivery_length ? values.delivery_length / 10 : (values.single_piece_length ? values.single_piece_length : undefined), // mm转cm
                  unit_width: values.delivery_width ? values.delivery_width / 10 : (values.single_piece_width ? values.single_piece_width : undefined), // mm转cm
                  // 其他字段
                  procurement_type: 'MAKE',
                  valuation_method: 'STANDARD',
                  currency: 'CNY'
                }
                
                // 创建物料
                const createdMaterialResponse = await api.post('/mm/materials', materialData)
                const createdMaterial = createdMaterialResponse.data || createdMaterialResponse
                message.success(`已自动创建产品主数据：${productNumber}`)
                
                // 自动填充产品名称
                if (createdMaterial && createdMaterial.material_name) {
                  form.setFieldsValue({ product_name: createdMaterial.material_name })
                  setSelectedProduct(createdMaterial)
                } else if (materialName) {
                  // 如果响应中没有material_name，使用创建时使用的名称
                  form.setFieldsValue({ product_name: materialName })
                }
                
                // 创建产品主数据映射（如果提供了客户ID）
                if (values.customer_id) {
                  try {
                    const mappingData = {
                      customer_id: values.customer_id,
                      factory_product_number: productNumber,
                      material_code: productNumber,
                      is_default: true,
                      effective_date: new Date().toISOString()
                    }
                    await api.post('/sd/factory-product-mappings', mappingData)
                  } catch (mappingError) {
                    // 映射创建失败不影响报价单创建，只记录日志
                    console.warn('创建产品主数据映射失败:', mappingError)
                  }
                }
              }
            }
            
            // 检查产品主数据映射是否存在（如果提供了客户ID）
            if (values.customer_id) {
              try {
                // 尝试查找产品主数据映射
                const mappingsResponse = await api.get('/sd/factory-product-mappings', {
                  params: {
                    customer_id: values.customer_id,
                    factory_product_number: productNumber,
                    limit: 1
                  }
                })
                const mappings = mappingsResponse.data || []
                
                // 如果映射不存在，创建映射
                if (mappings.length === 0) {
                  const mappingData = {
                    customer_id: values.customer_id,
                    factory_product_number: productNumber,
                    material_code: productNumber,
                    is_default: true,
                    effective_date: new Date().toISOString()
                  }
                  await api.post('/sd/factory-product-mappings', mappingData)
                }
              } catch (mappingError) {
                // 映射检查/创建失败不影响报价单创建，只记录日志
                console.warn('检查/创建产品主数据映射失败:', mappingError)
              }
            }
          } catch (error: any) {
            // 产品主数据创建失败不影响报价单创建，只记录警告
            console.warn('自动创建产品主数据失败:', error)
            message.warning('自动创建产品主数据失败，但报价单将继续创建')
          }
        }
      }

      // 构建个性化服务JSON
      const personalizedServices = {
        确认生产稿: values.production_draft_confirmation || '无需',
        华秋标识和制造周期: values.huaqiu_logo_cycle || '无需',
        周期格式: values.cycle_format || '周/年',
        客编: values.customer_code || '不加客编',
        打叉板: values.accept_scoring_board ? '接受打叉板' : '不接受打叉板',
        工程EQ确认方式: values.eq_confirmation_method || '平台推送',
        少数处理方式: values.minority_handling || '不设置',
        品质赔付方式: values.quality_compensation || '标准赔付',
        产品报告: {
          出货报告: values.shipping_report || false,
          切片报告: values.slice_report || false,
          实物菲林: values.physical_film || false
        },
        隔白纸: values.white_paper_isolation || '无需',
        内标签: values.inner_label || '无需',
        内包装标签备注: values.inner_label_remark || '',
        纸箱要求: values.carton_requirement || '华秋标识纸箱',
        审核通知: values.audit_notification || '无需'
      }

      // 从计算结果中获取价格明细，如果没有计算结果则使用默认值
      const engineeringFee = calculationResult?.engineering_fee || priceDetails.engineering_fee || 0
      const boardMaterialFee = calculationResult?.board_material_fee || priceDetails.board_material_fee_amount || 0
      const finalTotalPrice = calculationResult?.final_total_price || priceDetails.estimated_total_price || 0
      
      const formData = {
        ...values,
        valid_until: values.valid_until ? values.valid_until.toISOString() : undefined,
        personalized_services: personalizedServices,
        // 将single_piece_quantity同时赋值给quantity，保持后端兼容
        quantity: values.single_piece_quantity || 0,
        // 价格明细（从报价明细计算结果中获取）
        engineering_fee: engineeringFee,
        board_material_fee_amount: boardMaterialFee,
        via_fee: 0,  // 过孔费已整合到板材费中
        estimated_total_price: finalTotalPrice,
        // 保持unit_price字段用于后端兼容
        unit_price: finalTotalPrice
      }
      
      if (isEdit) {
        await api.put(`/sd/quotations/${id}`, formData)
        message.success('报价单更新成功')
      } else {
        await api.post('/sd/quotations', formData)
        message.success('报价单创建成功')
      }
      navigate('/sd/quotations')
    } catch (error: any) {
      const errorMsg = error.response?.data?.detail || error.message || '操作失败'
      message.error(errorMsg)
      console.error('报价单操作失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 报价计算结果表格列
  // 工序明细表格列
  const processColumns = [
    { title: 'NO', dataIndex: 'process_order', key: 'process_order', width: 60 },
    { title: '工序', dataIndex: 'process_name', key: 'process_name' },
    { title: 'P成本计算信息', dataIndex: 'p_cost_calculation_info', key: 'p_cost_calculation_info' },
    { title: 'P价格', dataIndex: 'p_price', key: 'p_price', render: (val: number) => `¥${val?.toFixed(4)}` },
    { title: '出货面积(m²)', dataIndex: 'delivery_area', key: 'delivery_area', render: (val: number) => val?.toFixed(4) },
    { title: '工序成本占(%)', dataIndex: 'process_cost_share', key: 'process_cost_share', render: (val: number) => `${val?.toFixed(2)}%` },
  ]

  return (
    <div>
      <Card title={isEdit ? '编辑报价单' : '新建报价单'}>
        <Form
          form={form}
          layout="vertical"
          onFinish={onFinish}
          initialValues={{
            set_per_unit: 1,
            test_points: 0,
            currency: 'CNY',
            layers: 4,
            panelization_count: 1,
            single_piece_unit: 'Pcs',
            line_width_spacing_unit: 'mil',
            hole_diameter_unit: 'mm',
            process_border_type: '无',
            process_border_size: 0,
            hdi_type: '无',
            holes_in_pads: '无',
            impedance: '无',
            finger_bevel: '无需',
            half_hole: '无需',
            edge_plating: '无需',
            press_fit_hole: '无需',
            test_method: '样品免费',
            shipping_notification: '无需',
            delivery_note: '电子版',
            invoice_type: '增值税(普通)发票',
            payment_method: '手动确认支付',
            smt_patch_required: false,
            output_format: '单片出货',
            times: 1
          }}
        >
          <Tabs 
            activeKey={activeTab} 
            onChange={handleTabChange}
            items={[
              {
                key: 'basic',
                label: '基本信息',
                children: (
                  <Collapse 
                    defaultActiveKey={['basic']} 
                    ghost
                    items={[
                      {
                        key: 'basic',
                        label: '基本信息',
                        children: (
                          <div>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="customer_id"
                    label="客户"
                    rules={[{ required: true, message: '请选择客户' }]}
                  >
                    <Select placeholder="请选择客户" showSearch>
                      {customers.map(customer => (
                        <Option key={customer.customer_id} value={customer.customer_id}>
                          {customer.legal_name} ({customer.customer_id})
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="product_number"
                    label="本厂编号"
                    rules={[{ required: true, message: '请输入本厂编号' }]}
                  >
                    <Input 
                      placeholder="如：HS1004ENIGAB01" 
                      onChange={async (e) => {
                        const productNumber = e.target.value.trim()
                        if (productNumber && productNumber.length === 14) {
                          // 自动获取产品名称
                          try {
                            const response = await api.get(`/mm/materials/${productNumber}`)
                            const material = response.data
                            if (material) {
                              setSelectedProduct(material)
                              form.setFieldsValue({ product_name: material.material_name })
                            } else {
                              setSelectedProduct(null)
                              form.setFieldsValue({ product_name: undefined })
                            }
                          } catch (error) {
                            // 产品不存在，清空产品名称
                            setSelectedProduct(null)
                            form.setFieldsValue({ product_name: undefined })
                          }
                        } else {
                          setSelectedProduct(null)
                          form.setFieldsValue({ product_name: undefined })
                        }
                      }}
                    />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="product_name"
                    label="产品名称"
                  >
                    <Input placeholder="输入本厂编号后自动填充，也可手动输入" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="valid_until"
                    label="有效期至"
                  >
                    <DatePicker style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="currency"
                    label="货币"
                    rules={[{ required: true, message: '请选择货币' }]}
                  >
                    <Select>
                      <Option value="CNY">CNY (人民币)</Option>
                      <Option value="USD">USD (美元)</Option>
                      <Option value="EUR">EUR (欧元)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="start">产品配置</Divider>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="product_category"
                    label="产品类别"
                  >
                    <Select 
                      placeholder="请选择产品类别"
                      onChange={() => {
                        const values = form.getFieldsValue()
                        calculatePrice(values)
                      }}
                    >
                      <Option value="FR-4">FR-4</Option>
                      <Option value="罗杰斯高频板">罗杰斯高频板</Option>
                      <Option value="CEM-1">CEM-1</Option>
                      <Option value="CEM-3">CEM-3</Option>
                      <Option value="FR-1">FR-1</Option>
                      <Option value="22F">22F</Option>
                      <Option value="FPC">FPC</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="hdi_type"
                    label="HDI(盲埋孔)"
                  >
                    <Select
                      onChange={() => {
                        const values = form.getFieldsValue()
                        calculatePrice(values)
                      }}
                    >
                      <Option value="无">无</Option>
                      <Option value="1阶">1阶</Option>
                      <Option value="2阶">2阶</Option>
                      <Option value="3阶">3阶</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="panelization_count"
                    label="拼版款数"
                  >
                    <InputNumber min={1} style={{ width: '100%' }} placeholder="拼版款数" />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="start">板材信息</Divider>
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item
                    name="layers"
                    label="层数"
                  >
                    <Select
                      onChange={() => {
                        const values = form.getFieldsValue()
                        calculatePrice(values)
                      }}
                    >
                      {[1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20].map(layer => (
                        <Option key={layer} value={layer}>{layer}层</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="material_type"
                    label="板材类型"
                  >
                    <Select>
                      <Option value="FR4">FR4</Option>
                      <Option value="高频板">高频板</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="tg_value"
                    label="TG值"
                  >
                    <Input placeholder="如：TG135" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="board_material_brand"
                    label="板材品牌"
                  >
                    <Select 
                      placeholder="请选择品牌"
                      onChange={() => {
                        const values = form.getFieldsValue()
                        calculatePrice(values)
                      }}
                    >
                      <Option value="建滔KB (A级)">建滔KB (A级)</Option>
                      <Option value="生益 (A级)">生益 (A级)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item
                    name="board_material_model"
                    label="型号"
                  >
                    <Input placeholder="如：KB6164" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="board_material_flame_retardant"
                    label="阻燃性"
                  >
                    <Input placeholder="如：94V-0" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="board_material_fee"
                    label="指定板材费"
                  >
                    <Input placeholder="如：不加价" />
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="start">尺寸信息</Divider>
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item
                    name="delivery_length"
                    label="出货长(mm)"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="长度" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="delivery_width"
                    label="出货宽(mm)"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="宽度" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="set_per_unit"
                    label="SET=U"
                  >
                    <InputNumber min={1} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="utilization_rate"
                    label="利用率(%)"
                  >
                    <InputNumber min={0} max={100} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item
                    name="single_piece_quantity"
                    label="订单数量"
                    rules={[{ required: true, message: '请输入订单数量' }]}
                  >
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="数量" />
                  </Form.Item>
                </Col>
                <Col span={6}>
                  <Form.Item
                    name="output_format"
                    label="出货形式"
                  >
                    <Select>
                      <Option value="单片出货">单片出货</Option>
                      <Option value="连片(按文件)">连片(按文件)</Option>
                      <Option value="连片(华秋代拼)">连片(华秋代拼)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item
                name="remarks"
                label="备注"
              >
                <TextArea rows={4} placeholder="请输入备注信息" />
              </Form.Item>
                          </div>
                        )
                      },
                      {
                        key: 'process',
                        label: '工艺信息',
                        children: (
                          <div>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="finished_board_thickness"
                    label="完成板厚"
                  >
                    <Select placeholder="请选择厚度">
                      {['0.6', '0.8', '1.0', '1.2', '1.6', '2.0', '2.5', '3.0', '3.2'].map(thickness => (
                        <Option key={thickness} value={thickness}>{thickness}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="outer_copper_thickness"
                    label="外层完成铜"
                  >
                    <Select>
                      {['1OZ', '2OZ', '3OZ', '4OZ'].map(thickness => (
                        <Option key={thickness} value={thickness}>{thickness}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="inner_copper_thickness"
                    label="内层铜厚"
                  >
                    <Select>
                      {['0.5oz', '1oz', '2oz', '3oz', '4oz'].map(thickness => (
                        <Option key={thickness} value={thickness}>{thickness}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="inner_layer_thickening" valuePropName="checked">
                    <Checkbox>内层加厚</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="outer_line_width_spacing_limit" valuePropName="checked">
                    <Checkbox>外层线宽/距&lt;=3.5mil 完成-基铜&gt;=35</Checkbox>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="min_line_width_spacing"
                    label="最小线宽线距"
                  >
                    <Select>
                      {['10/10', '8/8', '6/6', '5/5', '4/4', '3.5/3.5'].map(value => (
                        <Option key={value} value={value}>{value}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="line_width_spacing_unit"
                    label="线宽线距单位"
                  >
                    <Select>
                      <Option value="mil">mil</Option>
                      <Option value="mm">mm</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="min_hole_diameter"
                    label="最小孔径"
                  >
                    <Select>
                      {['0.3', '0.25', '0.2', '0.15'].map(value => (
                        <Option key={value} value={value}>{value}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="hole_diameter_unit"
                    label="孔径单位"
                  >
                    <Select>
                      <Option value="mm">mm</Option>
                      <Option value="mil">mil</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="solder_mask_color_detail"
                    label="阻焊颜色"
                  >
                    <Select>
                      {['绿色', '蓝色', '红色', '黄色', '黑色', '哑黑', '白色'].map(color => (
                        <Option key={color} value={color}>{color}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="character_color_detail"
                    label="字符颜色"
                  >
                    <Select>
                      <Option value="黑色">黑色</Option>
                      <Option value="白色">白色</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="times"
                    label="次数"
                  >
                    <Select>
                      {[1, 2, 3, 4].map(t => (
                        <Option key={t} value={t}>{t}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="specify_sun" valuePropName="checked">
                    <Checkbox>指定太阳</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="board_thickness_tolerance" valuePropName="checked">
                    <Checkbox>板厚公差&lt;+/-10%</Checkbox>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="via_plugging"
                    label="过孔塞孔"
                  >
                    <Select>
                      <Option value="阻焊塞孔">阻焊塞孔</Option>
                      <Option value="树脂塞孔">树脂塞孔</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="min_drill_bit"
                    label="最小钻咀"
                  >
                    <Select>
                      {['1', '0.5', '0.3', '0.2'].map(d => (
                        <Option key={d} value={d}>{d}</Option>
                      ))}
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="set_hole_count"
                    label="SET孔数"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="solder_mask_coverage"
                    label="阻焊覆盖"
                  >
                    <Select>
                      <Option value="过孔盖油">过孔盖油</Option>
                      <Option value="过孔开窗">过孔开窗</Option>
                      <Option value="过孔塞油墨">过孔塞油墨</Option>
                      <Option value="过孔塞树脂+电镀填平">过孔塞树脂+电镀填平</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="holes_in_pads"
                    label="盘中孔"
                  >
                    <Select>
                      <Option value="无">无</Option>
                      <Option value="有">有</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="surface_finish"
                    label="表面处理"
                  >
                    <Select>
                      <Option value="OSP">OSP</Option>
                      <Option value="有铅喷锡">有铅喷锡</Option>
                      <Option value="无铅喷锡">无铅喷锡</Option>
                      <Option value="沉金">沉金</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="acceptance_standard"
                    label="验收标准"
                  >
                    <Select>
                      <Option value="IPC CLASS-2">IPC CLASS-2</Option>
                      <Option value="IPC CLASS-3">IPC CLASS-3</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="routing_process"
                    label="锣程(MM)"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="v_score_process"
                    label="V程(MM/SET)"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={24}>
                  <Form.Item name="hard_gold" valuePropName="checked">
                    <Checkbox>硬金(金手指)</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={24}>
                  <Form.Item name="no_positioning_hole_routing" valuePropName="checked">
                    <Checkbox>无定位孔锣</Checkbox>
                  </Form.Item>
                </Col>
              </Row>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="test_points"
                    label="测试点数"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="pcs_conversion"
                    label="PCS换算"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="pnl_conversion"
                    label="PNL换算"
                  >
                    <InputNumber min={0} style={{ width: '100%' }} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="lamination_order"
                    label="层压顺序"
                  >
                    <Select>
                      <Option value="文件中有提供">文件中有提供</Option>
                      <Option value="由工程师提供">由工程师提供</Option>
                      <Option value="指定层压顺序">指定层压顺序</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="impedance"
                    label="阻抗"
                  >
                    <Select>
                      <Option value="无">无</Option>
                      <Option value="有">有</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="stackup_structure"
                    label="叠层结构"
                  >
                    <Select>
                      <Option value="无需求">无需求</Option>
                      <Option value="按客户指定叠层">按客户指定叠层</Option>
                      <Option value="华秋04161H03-7628(免费)">华秋04161H03-7628(免费)</Option>
                      <Option value="华秋04161H01-2116(免费)">华秋04161H01-2116(免费)</Option>
                      <Option value="华秋04161H02-1080(50元起)">华秋04161H02-1080(50元起)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="finger_bevel"
                    label="手指斜边"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="需要">需要</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="half_hole"
                    label="半孔"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="1边半孔">1边半孔</Option>
                      <Option value="2边半孔">2边半孔</Option>
                      <Option value="3边半孔">3边半孔</Option>
                      <Option value="4边半孔">4边半孔</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="edge_plating"
                    label="包边"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="1边包边">1边包边</Option>
                      <Option value="2边包边">2边包边</Option>
                      <Option value="3边包边">3边包边</Option>
                      <Option value="4边包边">4边包边</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="press_fit_hole"
                    label="压接孔"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="有">有 (孔径公差+/-0.05mm)</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="test_method"
                    label="测试方式"
                  >
                    <Select>
                      <Option value="样品免费">样品免费</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
                          </div>
                        )
                      },
                      {
                        key: 'personalized',
                        label: '个性化服务',
                        children: (
                          <div>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="production_draft_confirmation"
                    label="确认生产稿"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="需要(不允许自动确认)">需要(不允许自动确认)</Option>
                      <Option value="需要(超时系统自动确认)">需要(超时系统自动确认)</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="huaqiu_logo_cycle"
                    label="华秋标识和制造周期"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="周期">周期</Option>
                      <Option value="华秋logo+周期">华秋logo+周期</Option>
                      <Option value="华秋UL+周期">华秋UL+周期</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="cycle_format"
                    label="周期格式"
                  >
                    <Select>
                      <Option value="年/周">年/周</Option>
                      <Option value="周/年">周/年</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="customer_code"
                    label="客编"
                  >
                    <Select>
                      <Option value="加客编">加客编</Option>
                      <Option value="指定位置加客编">指定位置加客编</Option>
                      <Option value="不加客编">不加客编</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="accept_scoring_board"
                    label="打叉板"
                    valuePropName="checked"
                  >
                    <Switch checkedChildren="接受" unCheckedChildren="不接受" />
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="eq_confirmation_method"
                    label="工程EQ确认方式"
                  >
                    <Select>
                      <Option value="平台推送">平台推送</Option>
                      <Option value="发送邮件">发送邮件</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="minority_handling"
                    label="少数处理方式"
                  >
                    <Select>
                      <Option value="不设置">不设置</Option>
                      <Option value="少数默认退款">少数默认退款</Option>
                      <Option value="少数默认补料">少数默认补料</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="quality_compensation"
                    label="品质赔付方式"
                  >
                    <Select>
                      <Option value="标准赔付">标准赔付</Option>
                      <Option value="元器件全额赔付(特定品质)">元器件全额赔付(特定品质)</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Divider orientation="start">产品报告</Divider>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="shipping_report"
                    valuePropName="checked"
                  >
                    <Checkbox>出货报告</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="slice_report"
                    valuePropName="checked"
                  >
                    <Checkbox>切片报告</Checkbox>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="physical_film"
                    valuePropName="checked"
                  >
                    <Checkbox>实物菲林</Checkbox>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="white_paper_isolation"
                    label="隔白纸"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="需要">需要</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="inner_label"
                    label="内标签"
                  >
                    <Select>
                      <Option value="需要标签">需要标签</Option>
                      <Option value="自定义标签">自定义标签</Option>
                      <Option value="无需">无需</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="inner_label_remark"
                    label="内包装标签备注"
                  >
                    <Input placeholder="不超过10个文字,或15个数字" maxLength={15} />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="carton_requirement"
                    label="纸箱要求"
                  >
                    <Select>
                      <Option value="华秋标识纸箱">华秋标识纸箱</Option>
                      <Option value="空白纸箱">空白纸箱</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="audit_notification"
                    label="审核通知"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="需要">需要</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
                          </div>
                        )
                      },
                      {
                        key: 'shipping',
                        label: '地址 / 快递',
                        children: (
                          <div>
              <Row gutter={16}>
                <Col span={8}>
                  <Form.Item
                    name="shipping_notification"
                    label="发货通知"
                  >
                    <Select>
                      <Option value="无需">无需</Option>
                      <Option value="需要">需要</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={8}>
                  <Form.Item
                    name="delivery_note"
                    label="送货单"
                  >
                    <Select>
                      <Option value="电子版">电子版</Option>
                      <Option value="纸质版">纸质版</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="shipping_address"
                    label="收货地址"
                  >
                    <TextArea rows={3} placeholder="请输入收货地址" />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="express_company"
                    label="快递公司"
                  >
                    <Input placeholder="请输入快递公司" />
                  </Form.Item>
                </Col>
              </Row>
                          </div>
                        )
                      },
                      {
                        key: 'invoice',
                        label: '发票 / 支付',
                        children: (
                          <div>
              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item
                    name="invoice_type"
                    label="开票类型"
                  >
                    <Select>
                      <Option value="增值税(普通)发票">增值税(普通)发票</Option>
                      <Option value="数电增值税(专用)发票">数电增值税(专用)发票</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    name="payment_method"
                    label="订单支付方式"
                  >
                    <Select>
                      <Option value="自动扣款并确认">自动扣款并确认</Option>
                      <Option value="手动确认支付">手动确认支付</Option>
                    </Select>
                  </Form.Item>
                </Col>
              </Row>
                          </div>
                        )
                      },
                      {
                        key: 'smt',
                        label: 'SMT 贴片',
                        children: (
                          <div>
                            <Row gutter={16}>
                              <Col span={12}>
                                <Form.Item
                                  name="smt_patch_required"
                                  label="华秋SMT贴片"
                                  valuePropName="checked"
                                >
                                  <Switch checkedChildren="需要" unCheckedChildren="不需要" />
                                </Form.Item>
                              </Col>
                            </Row>
                          </div>
                        )
                      }
                    ]}
                  />
                )
              },
              {
                key: 'details',
                label: '报价明细',
                children: (
              <Row gutter={16}>
                {/* 左侧：板规格参数 */}
                <Col span={8}>
                  <Card title="板规格参数" size="small">
                    <Row gutter={[8, 8]}>
                      <Col span={12}>
                        <Form.Item name="layers" label="层数">
                          <Select onChange={(value) => syncDetailsToBasic('layers', value)}>
                            {[1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 18, 20].map(layer => (
                              <Option key={layer} value={layer}>{layer}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="utilization_rate" label="利用率(%)">
                          <InputNumber style={{ width: '100%' }} min={0} max={100} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="delivery_length" label="出货长(mm)">
                          <InputNumber 
                            style={{ width: '100%' }} 
                            min={0} 
                            onChange={(value) => syncDetailsToBasic('delivery_length', value)}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="delivery_width" label="出货宽(mm)">
                          <InputNumber 
                            style={{ width: '100%' }} 
                            min={0} 
                            onChange={(value) => syncDetailsToBasic('delivery_width', value)}
                          />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="set_per_unit" label="SET=U">
                          <InputNumber style={{ width: '100%' }} min={1} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="material_type" label="板材类型">
                          <Select onChange={(value) => syncDetailsToBasic('material_type', value)}>
                            <Option value="FR4">FR4</Option>
                            <Option value="高频板">高频板</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="tg_value" label="TG">
                          <Input onChange={(e) => syncDetailsToBasic('tg_value', e.target.value)} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="finished_board_thickness" label="完成板厚">
                          <Select onChange={(value) => syncDetailsToBasic('finished_board_thickness', value)}>
                            {['0.6', '0.8', '1.0', '1.2', '1.6', '2.0', '2.5', '3.0', '3.2'].map(t => (
                              <Option key={t} value={t}>{t}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="large_material_spec" label="大料规格">
                          <Select>
                            {['41', '42', '43'].map(s => (
                              <Option key={s} value={s}>{s}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="large_material_pnl_count" label="大料开PNL数">
                          <InputNumber style={{ width: '100%' }} min={1} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="pnl_set_count" label="PNL含SET数">
                          <InputNumber style={{ width: '100%' }} min={1} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="pnl_length_mm" label="PNL尺寸MM-长">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="pnl_width_mm" label="PNL尺寸MM-宽">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="core_board_count" label="芯板张数">
                          <InputNumber style={{ width: '100%' }} min={1} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="core_board_spec" label="芯板规格">
                          <Input />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="surface_finish" label="表面处理">
                          <Select onChange={(value) => syncDetailsToBasic('surface_finish', value)}>
                            <Option value="OSP">OSP</Option>
                            <Option value="有铅喷锡">有铅喷锡</Option>
                            <Option value="无铅喷锡">无铅喷锡</Option>
                            <Option value="沉金">沉金</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="outer_copper_thickness" label="外层完成铜">
                          <Select onChange={(value) => syncDetailsToBasic('outer_copper_thickness', value)}>
                            {['1OZ', '2OZ', '3OZ'].map(t => (
                              <Option key={t} value={t}>{t}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="inner_layer_thickening" valuePropName="checked">
                          <Checkbox>内层加厚</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="outer_line_width_spacing_limit" valuePropName="checked">
                          <Checkbox>外层线宽/距&lt;=3.5mil 完成-基铜&gt;=35</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="solder_mask_color_detail" label="阻焊颜色">
                          <Select onChange={(value) => syncDetailsToBasic('solder_mask_color_detail', value)}>
                            {['绿色', '蓝色', '红色', '黄色', '黑色', '哑黑', '白色'].map(c => (
                              <Option key={c} value={c}>{c}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="times" label="次数">
                          <Select>
                            {[1, 2, 3, 4].map(t => (
                              <Option key={t} value={t}>{t}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="specify_sun" valuePropName="checked">
                          <Checkbox>指定太阳</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="board_thickness_tolerance" valuePropName="checked">
                          <Checkbox>板厚公差&lt;+/-10%</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="via_plugging" label="过孔塞孔">
                          <Select onChange={(value) => syncDetailsToBasic('via_plugging', value)}>
                            <Option value="阻焊塞孔">阻焊塞孔</Option>
                            <Option value="树脂塞孔">树脂塞孔</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="character_color_detail" label="字符颜色">
                          <Select onChange={(value) => syncDetailsToBasic('character_color_detail', value)}>
                            <Option value="黑色">黑色</Option>
                            <Option value="白色">白色</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="min_drill_bit" label="最小钻咀">
                          <Select onChange={(value) => syncDetailsToBasic('min_drill_bit', value)}>
                            {['1', '0.5', '0.3', '0.2'].map(d => (
                              <Option key={d} value={d}>{d}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="set_hole_count" label="SET孔数">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="pcs_conversion" label="PCS换算">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="pnl_conversion" label="PNL换算">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="acceptance_standard" label="验收标准">
                          <Select>
                            <Option value="IPC CLASS-2">IPC CLASS-2</Option>
                            <Option value="IPC CLASS-3">IPC CLASS-3</Option>
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="routing_process" label="锣程(MM)">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="v_score_process" label="V程(MM/SET)">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="hard_gold" valuePropName="checked">
                          <Checkbox>硬金(金手指)</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="no_positioning_hole_routing" valuePropName="checked">
                          <Checkbox>无定位孔锣</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item name="test_points" label="测试点数">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 中间：加价选项 */}
                <Col span={8}>
                  <Card title="加价选项" size="small">
                    <Divider orientation="start">常规加价</Divider>
                    <Row gutter={[8, 8]}>
                      {['碳油', '蓝胶', '高温胶', '阻抗要求', 'PTH铣槽', '金属化半孔', '板边金属化包边', '控深锣', '压接孔(+/-0.05)', '孔铜>25um', '汽车板', '无卤', '不接受X板(SET=U>6)', 'IPC-3级标准', '外形公差<+/-0.1', '板厚公差<+/-10%', '6MIL以下线<+/-20%', '回流焊', '离子污染', '四线测试', 'BGA', '盲孔', '埋孔', '动态二维码'].map(item => (
                        <Col span={24} key={item}>
                          <Form.Item name={['regular_surcharges', item]} valuePropName="checked">
                            <Checkbox>{item}</Checkbox>
                          </Form.Item>
                        </Col>
                      ))}
                    </Row>
                    <Divider orientation="start">特殊加价</Divider>
                    <Row gutter={[8, 8]}>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '跳刀V0']} valuePropName="checked">
                          <Checkbox>跳刀V0</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '沉头孔/喇叭孔0']} valuePropName="checked">
                          <Checkbox>沉头孔/喇叭孔0</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '额外PP张数0']} valuePropName="checked">
                          <Checkbox>额外PP张数0</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '特殊PP']} valuePropName="checked">
                          <Checkbox>特殊PP</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '锣斜边/set 0']} valuePropName="checked">
                          <Checkbox>锣斜边/set 0</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '正常斜']} valuePropName="checked">
                          <Checkbox>正常斜</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name={['special_surcharges', '额外干膜次数0']} valuePropName="checked">
                          <Checkbox>额外干膜次数0</Checkbox>
                        </Form.Item>
                      </Col>
                    </Row>
                    <Divider orientation="start">其他</Divider>
                    <Row gutter={[8, 8]}>
                      <Col span={24}>
                        <Form.Item name="additional_surcharge_per_m2" label="额外加价/M2">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="customer_provides_hf_board" valuePropName="checked">
                          <Checkbox>客户提供高频板</Checkbox>
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="min_customer_consumption" label="收客户最低消费">
                          <InputNumber style={{ width: '100%' }} min={0} />
                        </Form.Item>
                      </Col>
                      <Col span={24}>
                        <Form.Item name="market_quote_remarks" label="市场报价备注">
                          <Input />
                        </Form.Item>
                      </Col>
                    </Row>
                  </Card>
                </Col>

                {/* 右侧：报价计算结果 */}
                <Col span={8}>
                  <Card 
                    title="报价计算结果" 
                    size="small"
                    extra={
                      <Button type="primary" size="small" onClick={calculateQuotationDetails}>
                        成本计算
                      </Button>
                    }
                  >
                    {calculationResult ? (
                      <>
                        {/* 产品规格信息 */}
                        <div style={{ marginBottom: 16, padding: '12px', background: 'hsl(var(--surface-hover))', borderRadius: '4px' }}>
                          <Row gutter={[16, 8]}>
                            <Col span={12}>
                              <div><strong>交期：</strong>{form.getFieldValue('delivery_time') || '正常48小时'}</div>
                            </Col>
                            <Col span={12}>
                              <div>
                                <strong>油墨：</strong>
                                <span style={{ 
                                  display: 'inline-block', 
                                  width: '12px', 
                                  height: '12px', 
                                  backgroundColor: form.getFieldValue('solder_mask_color_detail') === '绿色' ? 'hsl(var(--chart-success))' : 
                                                  form.getFieldValue('solder_mask_color_detail') === '蓝色' ? 'hsl(var(--brand))' :
                                                  form.getFieldValue('solder_mask_color_detail') === '红色' ? 'hsl(var(--destructive))' :
                                                  form.getFieldValue('solder_mask_color_detail') === '黄色' ? 'hsl(var(--chart-warning))' :
                                                  form.getFieldValue('solder_mask_color_detail') === '黑色' ? 'var(--color-swatch-black)' :
                                                  form.getFieldValue('solder_mask_color_detail') === '哑黑' ? 'var(--color-swatch-charcoal)' :
                                                  form.getFieldValue('solder_mask_color_detail') === '白色' ? 'var(--color-paper)' : 'hsl(var(--chart-success))',
                                  border: '1px solid hsl(var(--line-strong))',
                                  marginRight: '4px',
                                  verticalAlign: 'middle'
                                }}></span>
                                {form.getFieldValue('solder_mask_color_detail') || '绿色'}
                              </div>
                            </Col>
                            <Col span={12}>
                              <div><strong>板厚：</strong>{form.getFieldValue('finished_board_thickness') || '1.6'}</div>
                            </Col>
                            <Col span={12}>
                              <div><strong>加急费：</strong>{form.getFieldValue('expedited_fee') || '无'}</div>
                            </Col>
                          </Row>
                          <div style={{ marginTop: 12, fontSize: '12px', color: 'hsl(var(--ink-soft))' }}>
                            <div>• 当天18:00后付款,交期顺延1天</div>
                            <div>• 当天21:00后EQ处理完成的订单,交期顺延1天</div>
                            <div>• 周日只接单不安排生产,交期同周一-下单一致</div>
                          </div>
                        </div>

                        {/* 价格明细 */}
                        <div style={{ marginBottom: 16 }}>
                          <div style={{ fontWeight: 'bold', marginBottom: 8 }}>价格明细</div>
                          <Row gutter={[16, 8]}>
                            <Col span={12}>
                              <div><strong>工程费：</strong>¥{calculationResult.engineering_fee?.toFixed(2) || '0.00'}</div>
                            </Col>
                            <Col span={12}>
                              <div><strong>板材费：</strong>¥{calculationResult.board_material_fee?.toFixed(2) || (calculationResult.cost_per_m2 ? (calculationResult.cost_per_m2 * (calculationResult.delivery_area || 0)).toFixed(2) : '0.00')}</div>
                            </Col>
                          </Row>
                          <div style={{ marginTop: 8, fontSize: '12px', color: 'hsl(var(--ink-faint))' }}>
                            (仅供参考,最终价格以审核后为准)
                          </div>
                        </div>

                        {/* 预估总价 */}
                        <div style={{ 
                          marginBottom: 16, 
                          padding: '12px', 
                          background: 'hsl(var(--destructive) / 0.1)', 
                          borderRadius: '4px',
                          border: '1px solid hsl(var(--destructive) / 0.35)'
                        }}>
                          <div style={{ 
                            fontSize: '16px', 
                            fontWeight: 'bold', 
                            color: 'hsl(var(--destructive))',
                            textAlign: 'center'
                          }}>
                            预估总价: ¥{calculationResult.final_total_price?.toFixed(2) || '0.00'}
                          </div>
                        </div>

                      </>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '20px', color: 'hsl(var(--ink-faint))' }}>
                        点击"成本计算"按钮生成报价明细
                      </div>
                    )}
                    <Divider />
                    <div style={{ marginTop: 16 }}>
                      <div style={{ fontWeight: 'bold', marginBottom: 8 }}>报价关键信息</div>
                      <Table
                        columns={processColumns}
                        dataSource={processDetails}
                        pagination={false}
                        size="small"
                        rowKey="process_order"
                      />
                    </div>
                  </Card>
                </Col>
              </Row>
                )
              }
            ]}
          />

          <Divider />

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit" loading={loading} size="large">
                {isEdit ? '更新' : '创建'}
              </Button>
              <Button onClick={() => navigate('/sd/quotations')} size="large">
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default QuotationForm
