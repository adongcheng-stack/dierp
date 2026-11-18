import { create } from 'zustand'

interface OrderState {
  // 销售订单筛选条件
  salesOrderFilters: {
    customer_id?: string
    status?: string
    dateRange?: [string, string]
  }
  
  // 生产订单筛选条件
  productionOrderFilters: {
    sales_order_number?: string
    status?: string
    dateRange?: [string, string]
  }
  
  // Actions
  setSalesOrderFilters: (filters: Partial<OrderState['salesOrderFilters']>) => void
  setProductionOrderFilters: (filters: Partial<OrderState['productionOrderFilters']>) => void
  resetSalesOrderFilters: () => void
  resetProductionOrderFilters: () => void
}

const useOrderStore = create<OrderState>((set) => ({
  salesOrderFilters: {},
  productionOrderFilters: {},
  
  setSalesOrderFilters: (filters) =>
    set((state) => ({
      salesOrderFilters: { ...state.salesOrderFilters, ...filters }
    })),
  
  setProductionOrderFilters: (filters) =>
    set((state) => ({
      productionOrderFilters: { ...state.productionOrderFilters, ...filters }
    })),
  
  resetSalesOrderFilters: () =>
    set({ salesOrderFilters: {} }),
  
  resetProductionOrderFilters: () =>
    set({ productionOrderFilters: {} })
}))

export default useOrderStore

