import { create } from 'zustand'

interface Material {
  material_code: string
  material_name: string
  material_type: string
  status: string
  [key: string]: any
}

interface MaterialState {
  materials: Material[]
  loading: boolean
  filters: {
    material_type?: string
    status?: string
    keyword?: string
  }
  
  // Actions
  setMaterials: (materials: Material[]) => void
  setLoading: (loading: boolean) => void
  setFilters: (filters: Partial<MaterialState['filters']>) => void
  resetFilters: () => void
  getMaterialByCode: (code: string) => Material | undefined
}

const useMaterialStore = create<MaterialState>((set, get) => ({
  materials: [],
  loading: false,
  filters: {},
  
  setMaterials: (materials) => set({ materials }),
  
  setLoading: (loading) => set({ loading }),
  
  setFilters: (filters) =>
    set((state) => ({
      filters: { ...state.filters, ...filters }
    })),
  
  resetFilters: () => set({ filters: {} }),
  
  getMaterialByCode: (code) => {
    const materials = get().materials
    return materials.find((m) => m.material_code === code)
  }
}))

export default useMaterialStore

