/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_MOCK?: string
  readonly VITE_DEMO_OUT_DIR?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}