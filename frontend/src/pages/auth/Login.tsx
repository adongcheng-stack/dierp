import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { App as AntdApp, Button, Form, Input } from 'antd'
import {
  AlertCircle,
  ClipboardCheck,
  Eye,
  EyeOff,
  Factory,
  Lock,
  Moon,
  Package,
  ShoppingCart,
  Sun,
  User,
} from 'lucide-react'
import { useAuthStore } from '../../stores/authStore'
import { useThemeStore } from '../../stores/themeStore'
import { SliderCaptcha } from '../../components/common/SliderCaptcha'
import { isMockMode } from '../../mock'

const CAPABILITIES = [
  { icon: ShoppingCart, title: '销售与分销', desc: '客户建档 · 报价审批 · 销售订单' },
  { icon: Factory, title: '工程管理', desc: 'BOM · 工艺路线 · MI · 生产版本' },
  { icon: ClipboardCheck, title: '生产执行', desc: '工作中心 · 工单 · LOT卡 · 工序报工' },
  { icon: Package, title: '物料管理', desc: '物料主数据 · 生产领料 · 库存扣减' },
]

interface LoginFormValues {
  username: string
  password: string
}

const Login: React.FC = () => {
  const navigate = useNavigate()
  const { login } = useAuthStore()
  const { theme, toggleTheme } = useThemeStore()
  const { message } = AntdApp.useApp()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [captchaVerified, setCaptchaVerified] = useState(false)
  const [captchaResetSignal, setCaptchaResetSignal] = useState(0)

  const onFinish = async (values: LoginFormValues) => {
    if (!captchaVerified) {
      setError('请先完成安全验证')
      return
    }
    setError('')
    setSubmitting(true)
    try {
      await login(values.username, values.password)
      message.success('登录成功')
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || '登录失败，请检查用户名和密码'
      setError(detail)
      // 登录失败后要求重新完成安全验证
      setCaptchaVerified(false)
      setCaptchaResetSignal((value) => value + 1)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-sunken px-4 py-10">
      <div className="w-full max-w-[920px]">
        <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-pop">
          <div className="flex flex-col md:flex-row">
            {/* 左侧：系统信息（实心深色面，不做装饰渐变） */}
            <div className="flex flex-col bg-[hsl(var(--n-950))] p-8 md:w-[42%] md:p-10">
              <div className="flex items-center gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-white text-[#2662c9]">
                  <Factory className="h-6 w-6" />
                </div>
                <div className="min-w-0">
                  <h1 className="truncate text-2xl font-semibold leading-none tracking-tight text-white">
                    DIERP
                  </h1>
                  <p className="mt-1.5 truncate text-xs text-white/55">ERP 管理系统 · Demo</p>
                </div>
              </div>

              <ul className="mt-10 flex flex-1 flex-col justify-center gap-5">
                {CAPABILITIES.map(({ icon: Icon, title, desc }) => (
                  <li key={title} className="flex items-start gap-3">
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-white/55" aria-hidden="true" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-white/90">{title}</p>
                      <p className="mt-0.5 truncate text-xs text-white/55">{desc}</p>
                    </div>
                  </li>
                ))}
              </ul>

              <div className="mt-10">
                <p className="text-sm text-white/70">请使用分配的账号登录</p>
                <p className="mt-1 text-xs text-white/55">账号异常请联系系统管理员</p>
              </div>
            </div>

            {/* 右侧：登录表单 */}
            <div className="flex-1 p-8 md:p-10">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold tracking-tight text-ink">用户登录</h2>
                  <p className="mt-1 text-sm text-ink-soft">登录后进入 DIERP ERP 工作台</p>
                </div>
                <button
                  type="button"
                  onClick={toggleTheme}
                  className="-mr-1 -mt-1 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-ink-faint transition-colors hover:bg-surface-hover hover:text-ink"
                  title={theme === 'light' ? '切换到暗色模式' : '切换到亮色模式'}
                >
                  {theme === 'light' ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                </button>
              </div>

              {error && (
                <div
                  role="alert"
                  className="mb-4 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <Form<LoginFormValues>
                name="login"
                layout="vertical"
                requiredMark={false}
                onFinish={onFinish}
                autoComplete="off"
                initialValues={{ username: '', password: '' }}
              >
                <Form.Item
                  label="用户名"
                  name="username"
                  rules={[{ required: true, message: '请输入用户名' }]}
                >
                  <Input
                    size="large"
                    placeholder="请输入用户名"
                    autoComplete="username"
                    prefix={<User className="h-4 w-4 text-ink-faint" />}
                    className="h-11"
                  />
                </Form.Item>

                <Form.Item
                  label="密码"
                  name="password"
                  rules={[{ required: true, message: '请输入密码' }]}
                >
                  <Input
                    size="large"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="请输入密码"
                    autoComplete="current-password"
                    prefix={<Lock className="h-4 w-4 text-ink-faint" />}
                    suffix={
                      <button
                        type="button"
                        onClick={() => setShowPassword((value) => !value)}
                        aria-label={showPassword ? '隐藏密码' : '显示密码'}
                        className="inline-flex h-6 w-6 items-center justify-center rounded text-ink-faint transition-colors hover:text-ink"
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </button>
                    }
                    className="h-11"
                  />
                </Form.Item>

                <Form.Item label="安全验证" required className="mb-4">
                  <SliderCaptcha
                    disabled={submitting}
                    resetSignal={captchaResetSignal}
                    onVerified={() => setCaptchaVerified(true)}
                    onReset={() => setCaptchaVerified(false)}
                  />
                </Form.Item>

                <Button
                  type="primary"
                  htmlType="submit"
                  size="large"
                  block
                  loading={submitting}
                  className="mt-2 h-11"
                >
                  登录
                </Button>
              </Form>

              <p className="mt-6 text-xs text-ink-faint">
                {isMockMode ? (
                  <>
                    演示模式 · 登录任意已建账号，密码统一为{' '}
                    <span className="font-medium text-ink-soft">admin123</span>；所有操作仅保存在当前浏览器，可随时在右上角菜单「重置演示数据」。
                  </>
                ) : (
                  <>
                    默认账号 <span className="font-medium text-ink-soft">admin</span> /{' '}
                    <span className="font-medium text-ink-soft">admin123</span>，生产环境请立即修改。
                  </>
                )}
              </p>
            </div>
          </div>
        </div>

        <p className="mt-4 text-center text-xs text-ink-faint">
          DIERP ERP 管理系统 · Demo · 销售报价 → 工程数据 → 生产执行 → 物料管理
        </p>
      </div>
    </div>
  )
}

export default Login
