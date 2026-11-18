import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

/** 合并条件类名并处理 Tailwind 冲突（与 MES 前端同一实现） */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
