export type Role = 'manager' | 'staff'

export interface Profile {
  id: string
  restaurant_id: string
  full_name: string
  role: Role
}

export interface Restaurant {
  id: string
  name: string
  join_code: string
}

export interface Product {
  id: string
  restaurant_id: string
  name: string
  category: string
  unit: string
  par_level: number
}
