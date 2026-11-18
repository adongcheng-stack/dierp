import { createContext, useCallback, useContext, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Modal } from 'antd'
import { AlertTriangle, Info } from 'lucide-react'

/**
 * 统一确认弹窗
 * ----------------------------------------------------------------
 * 项目内所有二次确认（关闭 / 废弃 / 提交 / 退出登录 …）统一走这里，
 * 保证与普通表单弹窗一致的「图标 + 标题 + 关闭按钮 + 分隔线 + 底部按钮栏」结构。
 *
 * 用法：
 *   const confirm = useConfirm()
 *   confirm({ title: '确认关闭', content: '…', onOk: () => doSomething() })
 *
 * `onOk` 返回 Promise 时按钮会自动进入 loading，完成后关闭。
 */

export type ConfirmIconKind = 'info' | 'warning'

export interface ConfirmOptions {
  title?: ReactNode
  content?: ReactNode
  okText?: string
  cancelText?: string
  /** 标题图标语义，默认 info（品牌色）；删除 / 废弃类操作可用 warning */
  icon?: ConfirmIconKind
  /** 确认按钮是否使用危险色 */
  danger?: boolean
  width?: number
  /** 点击遮罩是否关闭，默认不关闭 */
  maskClosable?: boolean
  onOk?: () => void | Promise<void>
  onCancel?: () => void
}

type ConfirmFn = (options: ConfirmOptions) => void

const ConfirmContext = createContext<ConfirmFn | null>(null)

export function ConfirmProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [options, setOptions] = useState<ConfirmOptions>({})
  const optionsRef = useRef<ConfirmOptions>({})

  const confirm = useCallback<ConfirmFn>((next) => {
    optionsRef.current = next
    setOptions(next)
    setLoading(false)
    setOpen(true)
  }, [])

  const close = () => {
    setOpen(false)
    setLoading(false)
  }

  const handleOk = async () => {
    const onOk = optionsRef.current.onOk
    try {
      const result = onOk?.()
      if (result && typeof (result as Promise<void>).then === 'function') {
        setLoading(true)
        await result
      }
    } finally {
      close()
    }
  }

  const handleCancel = () => {
    optionsRef.current.onCancel?.()
    close()
  }

  const iconKind = options.icon ?? 'info'
  const icon =
    iconKind === 'warning' ? (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-destructive/10 text-destructive">
        <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
      </span>
    ) : (
      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand">
        <Info className="h-3.5 w-3.5" aria-hidden="true" />
      </span>
    )

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      <Modal
        open={open}
        title={
          options.title ? (
            <span className="flex items-center gap-2">
              {icon}
              {options.title}
            </span>
          ) : undefined
        }
        okText={options.okText ?? '确定'}
        cancelText={options.cancelText ?? '取消'}
        okButtonProps={{ danger: options.danger }}
        confirmLoading={loading}
        width={options.width ?? 420}
        maskClosable={options.maskClosable ?? false}
        onOk={handleOk}
        onCancel={handleCancel}
      >
        {options.content}
      </Modal>
    </ConfirmContext.Provider>
  )
}

export function useConfirm(): ConfirmFn {
  const context = useContext(ConfirmContext)
  if (!context) {
    throw new Error('useConfirm 必须在 ConfirmProvider 内使用')
  }
  return context
}
