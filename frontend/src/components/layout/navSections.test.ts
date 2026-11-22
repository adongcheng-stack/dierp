import { describe, expect, it } from 'vitest'
import { NAV_ITEMS } from './menuConfig'
import { NAV_SECTIONS } from './navSections'

describe('NAV_SECTIONS', () => {
  it('covers every top-level item exactly once in original order', () => {
    expect(NAV_SECTIONS.flatMap((section) => section.keys)).toEqual(
      NAV_ITEMS.map((item) => item.key)
    )
  })

  it('uses the three approved section titles in order', () => {
    expect(NAV_SECTIONS.map((section) => section.title)).toEqual([
      '工作台',
      '业务域',
      '系统',
    ])
  })
})
