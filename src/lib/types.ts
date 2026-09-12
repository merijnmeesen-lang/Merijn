export interface Product {
  id: string
  name: string
  category: string
  unit: string
  par_level: number
}

export interface StockCount {
  id: string
  product_id: string
  quantity: number
  counted_by: string
  counted_at: string
}

export interface WasteLog {
  id: string
  product_id: string
  quantity: number
  reason: string
  logged_by: string
  logged_at: string
}
