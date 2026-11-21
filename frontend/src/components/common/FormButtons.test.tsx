import type { ComponentProps } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import FormButtons from './FormButtons'

// antd 会在相邻汉字间插入空格（如「保 存」），用宽松正则匹配可访问名称
function button(name: string) {
  return screen.getByRole('button', { name: new RegExp(name.split('').join('\\s*')) })
}

function renderButtons(props: ComponentProps<typeof FormButtons> = {}) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <FormButtons {...props} />
    </MemoryRouter>
  )
}

describe('FormButtons', () => {
  it('默认渲染保存与取消按钮', () => {
    renderButtons()
    expect(button('保存')).toBeInTheDocument()
    expect(button('取消')).toBeInTheDocument()
  })

  it('点击保存触发 onSave', () => {
    const onSave = vi.fn()
    renderButtons({ onSave })
    fireEvent.click(button('保存'))
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('点击取消触发 onCancel', () => {
    const onCancel = vi.fn()
    renderButtons({ onCancel, cancelPath: '/sd/customers' })
    fireEvent.click(button('取消'))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('showCancel=false 时不渲染取消按钮', () => {
    renderButtons({ showCancel: false })
    expect(button('保存')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /取\s*消/ })).not.toBeInTheDocument()
  })

  it('loading 时保存按钮进入加载态', () => {
    renderButtons({ loading: true })
    // antd v5 的 loading 按钮不设置 disabled 属性，而是加 ant-btn-loading 类
    expect(button('保存')).toHaveClass('ant-btn-loading')
  })

  it('支持自定义按钮文案', () => {
    renderButtons({ saveText: '提交审核', cancelText: '返回' })
    expect(button('提交审核')).toBeInTheDocument()
    expect(button('返回')).toBeInTheDocument()
  })
})
