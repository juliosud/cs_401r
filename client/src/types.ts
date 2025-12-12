export interface Address {
  street: string
  city: string
  state: string
  zip: string
}

export interface Customer {
  id: string
  first_name: string
  last_name: string
  email: string
  phone: string
  address: Address
}

export interface Service {
  type: string
  date: string
  technician: string
  satisfaction_score: number
  notes?: string
  cost?: number
}

export interface WebhookPayload {
  event_type: string
  customer: Customer
  service_history: Service[]
  current_plan?: string
  upcoming_service?: {
    type: string
    scheduled_date: string
  }
  customer_lifetime_value: string
  account_created: string
  last_upsell_sent?: string
  payment_status: string
  property_info?: {
    type: string
    year_built?: number
    size_sqft?: number
    lot_features?: string[]
  }
}

export interface MockCustomer {
  name: string
  data: WebhookPayload
}

export interface ReferralMessage {
  messageId: string
  timestamp: number
  customerEmail: string
  customerName: string
  emailContent: string
  emailSubject: string
  llmGeneratorScore: number
  llmJudgeScore: number
  judgeApproved: boolean
  judgeFeedback: string
  judgeIssues?: string[]
  rejectionReason: string  // appropriateness, service_validity, or brand
  createdAt: string
  status: 'approved' | 'rejected' | 'pending'
  retryCount: number
  customerData: WebhookPayload
}

export type Status = 'approved' | 'rejected' | 'pending'

export interface ServiceCatalogItem {
  name: string
  description: string
  ideal_for: string
  upsell_triggers: string[]
  benefits: string[]
}

export interface ServiceCatalog {
  preventive_services: ServiceCatalogItem[]
  specialized_treatments: ServiceCatalogItem[]
  add_on_services: ServiceCatalogItem[]
}

