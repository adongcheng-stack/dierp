import { describe, expect, it } from 'vitest'
import {
  READ_OPEN_DOMAINS,
  READ_ROLE_POLICY,
  WRITE_METHODS,
  WRITE_ROLE_POLICY,
} from './authorization.generated'

describe('本体生成的安全策略', () => {
  it('finance 域写角色显式包含 FINANCE（原漏洞回归）', () => {
    expect(WRITE_ROLE_POLICY.finance).toContain('FINANCE')
    expect(WRITE_ROLE_POLICY.finance).toContain('ADMIN')
    expect(WRITE_ROLE_POLICY.finance).not.toContain('WAREHOUSE')
  })

  it('未声明写策略的域为空集合，供 fail-closed 判定', () => {
    expect(WRITE_ROLE_POLICY.auth).toEqual([])
    expect(WRITE_ROLE_POLICY.traceability).toEqual([])
  })

  it('users/admin 域读策略受限，其余域匿名可读', () => {
    expect(READ_ROLE_POLICY.users).toEqual(['ADMIN'])
    expect(READ_ROLE_POLICY.admin).toEqual(['ADMIN'])
    expect(READ_OPEN_DOMAINS).toContain('sd')
    expect(READ_OPEN_DOMAINS).not.toContain('users')
  })

  it('写方法集合覆盖四种 HTTP 写方法', () => {
    expect([...WRITE_METHODS].sort()).toEqual(['DELETE', 'PATCH', 'POST', 'PUT'])
  })
})
