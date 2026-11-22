import { NAV_ITEMS } from './menuConfig'

export interface NavSection {
  title: string
  keys: string[]
}

export const NAV_SECTIONS: NavSection[] = [
  { title: '工作台', keys: ['/', 'kpi'] },
  {
    title: '业务域',
    keys: ['sd', 'pp', 'purchase', 'inventory', 'finance', 'eng', 'cost', 'qms', 'eam', 'aps'],
  },
  { title: '系统', keys: ['admin'] },
]

const allKeys = NAV_SECTIONS.flatMap((section) => section.keys)

if (allKeys.length !== NAV_ITEMS.length || allKeys.some((key, index) => key !== NAV_ITEMS[index].key)) {
  throw new Error('NAV_SECTIONS must preserve menuConfig order and cover every top-level item')
}
