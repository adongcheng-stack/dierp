import { lazy, Suspense } from 'react'
import { BrowserRouter, HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import AppLayout from './components/layout/AppLayout'
import Dashboard from './pages/Dashboard'
import { useAuthStore } from './stores/authStore'
import { isMockMode } from './mock'

/**
 * 路由级懒加载：首屏只加载布局 + 工作台，其余页面按访问需求加载。
 * 演示包体积较大（antd 全量组件），分包后首屏明显更快。
 */
const Login = lazy(() => import('./pages/auth/Login'))
const CustomerList = lazy(() => import('./pages/sd/CustomerList'))
const CustomerForm = lazy(() => import('./pages/sd/CustomerForm'))
const QuotationList = lazy(() => import('./pages/sd/QuotationList'))
const QuotationForm = lazy(() => import('./pages/sd/QuotationForm'))
const PendingApprovalList = lazy(() => import('./pages/sd/PendingApprovalList'))
const SalesOrderList = lazy(() => import('./pages/sd/SalesOrderList'))
const SalesOrderForm = lazy(() => import('./pages/sd/SalesOrderForm'))
const FactoryProductMappingList = lazy(() => import('./pages/sd/FactoryProductMappingList'))
const FactoryProductMappingForm = lazy(() => import('./pages/sd/FactoryProductMappingForm'))
const DeliveryList = lazy(() => import('./pages/sd/DeliveryList'))
const InvoiceList = lazy(() => import('./pages/sd/InvoiceList'))
const ReceivableView = lazy(() => import('./pages/sd/ReceivableView'))
const MaterialList = lazy(() => import('./pages/mm/MaterialList'))
const MaterialForm = lazy(() => import('./pages/mm/MaterialForm'))
const MaterialIssueList = lazy(() => import('./pages/mm/MaterialIssueList'))
const MaterialIssueForm = lazy(() => import('./pages/mm/MaterialIssueForm'))
const InventoryLedger = lazy(() => import('./pages/mm/InventoryLedger'))
const SupplierList = lazy(() => import('./pages/mm/SupplierList'))
const ApView = lazy(() => import('./pages/mm/ApView'))
const PurchaseRequestList = lazy(() => import('./pages/mm/PurchaseRequestList'))
const PurchaseReturnList = lazy(() => import('./pages/mm/PurchaseReturnList'))
const InventoryTransactions = lazy(() => import('./pages/mm/InventoryTransactions'))
const BOMList = lazy(() => import('./pages/eng/BOMList'))
const BOMForm = lazy(() => import('./pages/eng/BOMForm'))
const RoutingList = lazy(() => import('./pages/eng/RoutingList'))
const RoutingForm = lazy(() => import('./pages/eng/RoutingForm'))
const ProductionVersionList = lazy(() => import('./pages/eng/ProductionVersionList'))
const ProductionVersionForm = lazy(() => import('./pages/eng/ProductionVersionForm'))
const MIList = lazy(() => import('./pages/eng/MIList'))
const MIForm = lazy(() => import('./pages/eng/MIForm'))
const MIReview = lazy(() => import('./pages/eng/MIReview'))
const WorkCenterList = lazy(() => import('./pages/pp/WorkCenterList'))
const WorkCenterForm = lazy(() => import('./pages/pp/WorkCenterForm'))
const ProductionOrderList = lazy(() => import('./pages/pp/ProductionOrderList'))
const ProductionOrderForm = lazy(() => import('./pages/pp/ProductionOrderForm'))
const OperationReportList = lazy(() => import('./pages/pp/OperationReportList'))
const OperationReportForm = lazy(() => import('./pages/pp/OperationReportForm'))
const LotCardList = lazy(() => import('./pages/pp/LotCardList'))
const TraceabilityExplorer = lazy(() => import('./pages/traceability/TraceabilityExplorer'))
const ManagementDashboard = lazy(() => import('./pages/dashboard/ManagementDashboard'))
const PurchaseOrderList = lazy(() => import('./pages/planning/PurchaseOrderList'))
const LotCardForm = lazy(() => import('./pages/pp/LotCardForm'))
const PlanningWorkbench = lazy(() => import('./pages/planning/PlanningWorkbench'))
const MpsList = lazy(() => import('./pages/planning/MpsList'))
const MrpRunList = lazy(() => import('./pages/planning/MrpRunList'))
const PlannedOrderList = lazy(() => import('./pages/planning/PlannedOrderList'))
const PlanningExceptionList = lazy(() => import('./pages/planning/PlanningExceptionList'))
const KittingList = lazy(() => import('./pages/planning/KittingList'))
const PlanningPolicyList = lazy(() => import('./pages/planning/PlanningPolicyList'))
const CostWorkbench = lazy(() => import('./pages/cost/CostWorkbench'))
const StandardCostList = lazy(() => import('./pages/cost/StandardCostList'))
const ProductionCostList = lazy(() => import('./pages/cost/ProductionCostList'))
const CostVarianceList = lazy(() => import('./pages/cost/CostVarianceList'))
const CostSettlementList = lazy(() => import('./pages/cost/CostSettlementList'))
const CostRateList = lazy(() => import('./pages/cost/CostRateList'))
const ApsWorkbench = lazy(() => import('./pages/aps/ApsWorkbench'))
const ScheduleRunList = lazy(() => import('./pages/aps/ScheduleRunList'))
const ScenarioSimulationList = lazy(() => import('./pages/aps/ScenarioSimulationList'))
const ScheduleExceptionList = lazy(() => import('./pages/aps/ScheduleExceptionList'))
const ApsMasterData = lazy(() => import('./pages/aps/ApsMasterData'))
const EamWorkbench = lazy(() => import('./pages/eam/EamWorkbench'))
const MaintenancePlanList = lazy(() => import('./pages/eam/MaintenancePlanList'))
const MaintenanceOrderList = lazy(() => import('./pages/eam/MaintenanceOrderList'))
const EquipmentFailureList = lazy(() => import('./pages/eam/EquipmentFailureList'))
const QmsWorkbench = lazy(() => import('./pages/qms/QmsWorkbench'))
const InspectionList = lazy(() => import('./pages/qms/InspectionList'))
const NcrList = lazy(() => import('./pages/qms/NcrList'))
const UserList = lazy(() => import('./pages/admin/UserList'))
const UserForm = lazy(() => import('./pages/admin/UserForm'))

/** 演示包通常直接以静态文件打开，使用 hash 路由避免刷新 404 */
const Router = isMockMode ? HashRouter : BrowserRouter

function PageLoading() {
  return (
    <div className="flex min-h-[60vh] w-full items-center justify-center">
      <Spin size="large" tip="页面加载中…">
        <div className="h-12 w-32" />
      </Spin>
    </div>
  )
}

function App() {
  const { isAuthenticated } = useAuthStore()

  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Suspense
        fallback={
          <div className="flex min-h-screen items-center justify-center bg-canvas">
            <div className="flex flex-col items-center gap-3">
              <Spin size="large" />
              <span className="text-sm text-ink-soft">正在加载…</span>
            </div>
          </div>
        }
      >
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              isAuthenticated ? (
                <AppLayout>
                  <Suspense fallback={<PageLoading />}>
                    <Routes>
                      <Route path="/" element={<Dashboard />} />
                      <Route path="/sd/customers" element={<CustomerList />} />
                      <Route path="/sd/customers/new" element={<CustomerForm />} />
                      <Route path="/sd/customers/:id/edit" element={<CustomerForm />} />
                      <Route path="/sd/quotations" element={<QuotationList />} />
                      <Route path="/sd/quotations/new" element={<QuotationForm />} />
                      <Route path="/sd/quotations/:id/edit" element={<QuotationForm />} />
                      <Route path="/sd/pending-approvals" element={<PendingApprovalList />} />
                      <Route path="/sd/sales-orders" element={<SalesOrderList />} />
                      <Route path="/sd/sales-orders/new" element={<SalesOrderForm />} />
                      <Route path="/sd/sales-orders/:id/edit" element={<SalesOrderForm />} />
                      <Route path="/sd/deliveries" element={<DeliveryList />} />
                      <Route path="/sd/invoices" element={<InvoiceList />} />
                      <Route path="/sd/receivables" element={<ReceivableView />} />
                      <Route path="/mm/materials" element={<MaterialList />} />
                      <Route path="/mm/materials/new" element={<MaterialForm />} />
                      <Route path="/mm/materials/:code/edit" element={<MaterialForm />} />
                      <Route path="/mm/material-issues" element={<MaterialIssueList />} />
                      <Route path="/mm/material-issues/new" element={<MaterialIssueForm />} />
                      <Route path="/mm/inventory" element={<InventoryLedger />} />
                      <Route path="/mm/transactions" element={<InventoryTransactions />} />
                      <Route path="/mm/suppliers" element={<SupplierList />} />
                      <Route path="/mm/ap-view" element={<ApView />} />
                      <Route path="/mm/purchase-requests" element={<PurchaseRequestList />} />
                      <Route path="/mm/purchase-returns" element={<PurchaseReturnList />} />
                      <Route path="/eng/boms" element={<BOMList />} />
                      <Route path="/eng/factory-product-mappings" element={<FactoryProductMappingList />} />
                      <Route path="/eng/factory-product-mappings/new" element={<FactoryProductMappingForm />} />
                      <Route path="/eng/factory-product-mappings/:id/edit" element={<FactoryProductMappingForm />} />
                      <Route path="/eng/boms/new" element={<BOMForm />} />
                      <Route path="/eng/boms/:id/edit" element={<BOMForm />} />
                      <Route path="/eng/routings" element={<RoutingList />} />
                      <Route path="/eng/routings/new" element={<RoutingForm />} />
                      <Route path="/eng/routings/:id/edit" element={<RoutingForm />} />
                      <Route path="/eng/production-versions" element={<ProductionVersionList />} />
                      <Route path="/eng/production-versions/new" element={<ProductionVersionForm />} />
                      <Route path="/eng/production-versions/:id/edit" element={<ProductionVersionForm />} />
                      <Route path="/eng/mis" element={<MIList />} />
                      <Route path="/eng/mis/new" element={<MIForm />} />
                      <Route path="/eng/mis/:id/edit" element={<MIForm />} />
                      <Route path="/eng/mis/:id/review" element={<MIReview />} />
                      <Route path="/pp/work-centers" element={<WorkCenterList />} />
                      <Route path="/pp/work-centers/new" element={<WorkCenterForm />} />
                      <Route path="/pp/work-centers/:id/edit" element={<WorkCenterForm />} />
                      <Route path="/pp/production-orders" element={<ProductionOrderList />} />
                      <Route path="/pp/production-orders/new" element={<ProductionOrderForm />} />
                      <Route path="/pp/production-orders/:id/edit" element={<ProductionOrderForm />} />
                      <Route path="/pp/operation-reports" element={<OperationReportList />} />
                      <Route path="/pp/operation-reports/new" element={<OperationReportForm />} />
                      <Route path="/pp/lot-cards" element={<LotCardList />} />
                      <Route path="/pp/lot-cards/:lotNumber/edit" element={<LotCardForm />} />
                      <Route path="/trace/explorer" element={<TraceabilityExplorer />} />
                      <Route path="/dashboard/management" element={<ManagementDashboard />} />
                      <Route path="/mm/purchase-orders" element={<PurchaseOrderList />} />
                      <Route path="/pp/planning" element={<PlanningWorkbench />} />
                      <Route path="/pp/mps" element={<MpsList />} />
                      <Route path="/pp/mrp" element={<MrpRunList />} />
                      <Route path="/pp/planned-orders" element={<PlannedOrderList />} />
                      <Route path="/pp/planning-exceptions" element={<PlanningExceptionList />} />
                      <Route path="/pp/kitting" element={<KittingList />} />
                      <Route path="/pp/planning-policies" element={<PlanningPolicyList />} />
                      <Route path="/cost/workbench" element={<CostWorkbench />} />
                      <Route path="/cost/standard" element={<StandardCostList />} />
                      <Route path="/cost/production" element={<ProductionCostList />} />
                      <Route path="/cost/variances" element={<CostVarianceList />} />
                      <Route path="/cost/settlements" element={<CostSettlementList />} />
                      <Route path="/cost/rates" element={<CostRateList />} />
                      <Route path="/aps/workbench" element={<ApsWorkbench />} />
                      <Route path="/aps/runs" element={<ScheduleRunList />} />
                      <Route path="/aps/scenarios" element={<ScenarioSimulationList />} />
                      <Route path="/aps/exceptions" element={<ScheduleExceptionList />} />
                      <Route path="/aps/master-data" element={<ApsMasterData />} />
                      <Route path="/eam/workbench" element={<EamWorkbench />} />
                      <Route path="/eam/plans" element={<MaintenancePlanList />} />
                      <Route path="/eam/orders" element={<MaintenanceOrderList />} />
                      <Route path="/eam/failures" element={<EquipmentFailureList />} />
                      <Route path="/qms/workbench" element={<QmsWorkbench />} />
                      <Route path="/qms/inspections" element={<InspectionList />} />
                      <Route path="/qms/ncrs" element={<NcrList />} />
                      <Route path="/admin/users" element={<UserList />} />
                      <Route path="/admin/users/new" element={<UserForm />} />
                      <Route path="/admin/users/:id/edit" element={<UserForm />} />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                  </Suspense>
                </AppLayout>
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
        </Routes>
      </Suspense>
    </Router>
  )
}

export default App
