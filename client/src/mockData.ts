import { MockCustomer } from './types'

export const mockCustomers: MockCustomer[] = [
  {
    name: "Happy One-Time Customer → Quarterly Plan",
    data: {
      event_type: "service_completed",
      customer: {
        id: "CUST-12345",
        first_name: "Sarah",
        last_name: "Martinez",
        email: "sarah.martinez@example.com",
        phone: "+1-555-0123",
        address: {
          street: "742 Oakwood Drive",
          city: "Austin",
          state: "TX",
          zip: "78704"
        }
      },
      service_history: [
        {
          type: "One-Time Ant Treatment",
          date: "2024-12-10",
          technician: "Mike Johnson",
          satisfaction_score: 5,
          notes: "Successfully treated sugar ants in kitchen. Customer mentioned this is the third time this year they've had issues.",
          cost: 125
        },
        {
          type: "One-Time Ant Treatment",
          date: "2024-08-15",
          technician: "Carlos Rivera",
          satisfaction_score: 4,
          notes: "Treated ant infestation in kitchen and bathroom.",
          cost: 125
        },
        {
          type: "One-Time Spider Control",
          date: "2024-03-22",
          technician: "Jennifer Lee",
          satisfaction_score: 5,
          notes: "Removed spider webs and treated perimeter.",
          cost: 95
        }
      ],
      current_plan: "One-time services only",
      upcoming_service: undefined,
      customer_lifetime_value: "medium",
      account_created: "2024-03-15",
      payment_status: "current",
      property_info: {
        type: "Single Family Home",
        year_built: 2015,
        size_sqft: 2200,
        lot_features: ["backyard", "wood deck"]
      }
    }
  },
  {
    name: "Older Home → Termite Protection",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_002",
        first_name: "Robert",
        last_name: "Chen",
        email: "robert.chen@example.com",
        phone: "(555) 987-6543",
        address: {
          street: "1847 Victorian Lane",
          city: "Portland",
          state: "OR",
          zip: "97201"
        }
      },
      service_history: [
        {
          type: "General Pest Control",
          date: "2025-12-10",
          technician: "David Chen",
          satisfaction_score: 5,
          notes: "Quarterly service completed. Customer owns a beautiful 1920s Craftsman home. Noticed some wood damage in garage that could attract termites.",
          cost: 85
        },
        {
          type: "General Pest Control",
          date: "2025-09-08",
          technician: "David Chen",
          satisfaction_score: 5,
          notes: "Routine quarterly treatment. No issues reported.",
          cost: 85
        },
        {
          type: "General Pest Control",
          date: "2025-06-12",
          technician: "Lisa Martinez",
          satisfaction_score: 4,
          notes: "Found some carpenter ants near foundation. Treated area.",
          cost: 85
        },
        {
          type: "General Pest Control",
          date: "2025-03-20",
          technician: "David Chen",
          satisfaction_score: 5,
          notes: "Spring service completed successfully.",
          cost: 85
        },
        {
          type: "Initial Inspection & Treatment",
          date: "2024-12-05",
          technician: "Mike Johnson",
          satisfaction_score: 5,
          notes: "New customer. Historic home needs regular monitoring.",
          cost: 150
        }
      ],
      current_plan: "Quarterly Pest Control Plan",
      upcoming_service: {
        type: "Quarterly Pest Control",
        scheduled_date: "2026-03-10"
      },
      customer_lifetime_value: "high",
      account_created: "2024-12-01",
      payment_status: "current",
      property_info: {
        type: "Historic Craftsman",
        year_built: 1923,
        size_sqft: 2800,
        lot_features: ["mature trees", "wood siding", "detached garage"]
      }
    }
  },
  {
    name: "Service Complaint - Low Satisfaction",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_003",
        first_name: "Michael",
        last_name: "Rodriguez",
        email: "michael.rodriguez@example.com",
        phone: "(555) 234-5678",
        address: {
          street: "789 Oak Avenue",
          city: "Seattle",
          state: "WA",
          zip: "98101"
        }
      },
      service_history: [
        {
          type: "Ant Control",
          date: "2025-12-05",
          technician: "Lisa Martinez",
          satisfaction_score: 2,
          notes: "Customer filed complaint about treatment not being effective. Ants returned within a week. Offering free re-treatment.",
          cost: 0
        },
        {
          type: "Ant Control",
          date: "2025-11-28",
          technician: "Tom Anderson",
          satisfaction_score: 3,
          notes: "Initial treatment for ant infestation in kitchen.",
          cost: 125
        },
        {
          type: "General Pest Control",
          date: "2025-09-10",
          technician: "Carlos Rivera",
          satisfaction_score: 4,
          notes: "Routine service completed.",
          cost: 85
        }
      ],
      current_plan: "General Pest Control (one-time)",
      upcoming_service: {
        type: "Re-treatment (Complimentary)",
        scheduled_date: "2025-12-18"
      },
      customer_lifetime_value: "medium",
      account_created: "2025-08-15",
      payment_status: "current"
    }
  },
  {
    name: "Spring Season → Mosquito Treatment",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_004",
        first_name: "Emily",
        last_name: "Thompson",
        email: "emily.thompson@example.com",
        phone: "(555) 876-5432",
        address: {
          street: "321 Lakeview Terrace",
          city: "Austin",
          state: "TX",
          zip: "78701"
        }
      },
      service_history: [
        {
          type: "Quarterly Pest Control",
          date: "2025-11-28",
          technician: "Robert Kim",
          satisfaction_score: 5,
          notes: "Customer mentioned they have a large backyard with pool area. Family loves spending time outdoors. Asked if we offer mosquito treatments for summer.",
          cost: 95
        },
        {
          type: "Quarterly Pest Control",
          date: "2025-08-30",
          technician: "Robert Kim",
          satisfaction_score: 5,
          notes: "Everything looking great. Customer very happy with service.",
          cost: 95
        },
        {
          type: "Quarterly Pest Control",
          date: "2025-05-25",
          technician: "Robert Kim",
          satisfaction_score: 5,
          notes: "Spring treatment completed. Pool area inspected.",
          cost: 95
        },
        {
          type: "Quarterly Pest Control",
          date: "2025-02-20",
          technician: "Jennifer Lee",
          satisfaction_score: 4,
          notes: "Winter service. No issues.",
          cost: 95
        }
      ],
      current_plan: "Quarterly Pest Control Plan",
      upcoming_service: {
        type: "Quarterly Pest Control",
        scheduled_date: "2026-02-28"
      },
      customer_lifetime_value: "very_high",
      account_created: "2023-01-15",
      payment_status: "current",
      property_info: {
        type: "Single Family Home",
        year_built: 2018,
        size_sqft: 3200,
        lot_features: ["pool", "large backyard", "outdoor kitchen", "mature landscaping"]
      }
    }
  },
  {
    name: "Late Technician - Customer Frustrated",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_005",
        first_name: "James",
        last_name: "Wilson",
        email: "james.wilson@example.com",
        phone: "(555) 345-6789",
        address: {
          street: "555 Maple Drive",
          city: "Denver",
          state: "CO",
          zip: "80201"
        }
      },
      service_history: [
        {
          type: "Rodent Control",
          date: "2025-12-08",
          technician: "Amanda Brown",
          satisfaction_score: 3,
          notes: "Technician arrived 90 minutes late due to traffic. Customer had to rearrange work schedule. Service completed successfully but customer expressed frustration about timing.",
          cost: 175
        },
        {
          type: "Rodent Inspection",
          date: "2025-11-30",
          technician: "Tom Anderson",
          satisfaction_score: 4,
          notes: "Found evidence of mice in attic. Scheduled treatment.",
          cost: 75
        },
        {
          type: "General Pest Control",
          date: "2025-09-15",
          technician: "Mike Johnson",
          satisfaction_score: 5,
          notes: "Routine service. Customer happy.",
          cost: 85
        },
        {
          type: "General Pest Control",
          date: "2025-06-10",
          technician: "Mike Johnson",
          satisfaction_score: 5,
          notes: "Spring treatment completed.",
          cost: 85
        }
      ],
      current_plan: "General Pest Control (one-time)",
      upcoming_service: {
        type: "Rodent Follow-up",
        scheduled_date: "2026-01-08"
      },
      customer_lifetime_value: "medium",
      account_created: "2025-05-20",
      payment_status: "current"
    }
  },
  {
    name: "Attic Noises → Wildlife Removal",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_006",
        first_name: "Amanda",
        last_name: "Park",
        email: "amanda.park@example.com",
        phone: "(555) 456-7890",
        address: {
          street: "888 Forest Ridge",
          city: "Seattle",
          state: "WA",
          zip: "98102"
        }
      },
      service_history: [
        {
          type: "Monthly Pest Control",
          date: "2025-12-01",
          technician: "Carlos Rivera",
          satisfaction_score: 5,
          notes: "Customer mentioned hearing scratching sounds in attic at night. Concerned it might be squirrels or raccoons. Asked if we handle wildlife.",
          cost: 75
        },
        {
          type: "Monthly Pest Control",
          date: "2025-11-01",
          technician: "Carlos Rivera",
          satisfaction_score: 5,
          notes: "Monthly service completed. All good.",
          cost: 75
        },
        {
          type: "Monthly Pest Control",
          date: "2025-10-01",
          technician: "Carlos Rivera",
          satisfaction_score: 5,
          notes: "Routine treatment. Customer very satisfied.",
          cost: 75
        }
      ],
      current_plan: "Monthly Pest Control Plan",
      upcoming_service: {
        type: "Monthly Pest Control",
        scheduled_date: "2026-01-01"
      },
      customer_lifetime_value: "high",
      account_created: "2024-06-15",
      payment_status: "current",
      property_info: {
        type: "Single Family Home",
        year_built: 2005,
        size_sqft: 2400,
        lot_features: ["wooded lot", "attic space", "deck"]
      }
    }
  },
  {
    name: "Recurring Issues → Monthly Plan Upgrade",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_007",
        first_name: "David",
        last_name: "Kumar",
        email: "david.kumar@example.com",
        phone: "(555) 567-8901",
        address: {
          street: "2340 Creek Side",
          city: "Houston",
          state: "TX",
          zip: "77002"
        }
      },
      service_history: [
        {
          type: "Emergency Call - Roaches",
          date: "2025-12-05",
          technician: "Jennifer Lee",
          satisfaction_score: 4,
          notes: "Emergency treatment between quarterly visits. Property backs up to wooded area. Dealing with roaches frequently.",
          cost: 150
        },
        {
          type: "Quarterly Pest Control",
          date: "2025-09-20",
          technician: "Mike Johnson",
          satisfaction_score: 4,
          notes: "Routine service. Customer reported seeing more spiders than usual.",
          cost: 95
        },
        {
          type: "Emergency Call - Spiders",
          date: "2025-08-10",
          technician: "Tom Anderson",
          satisfaction_score: 4,
          notes: "Customer called for emergency spider treatment.",
          cost: 125
        },
        {
          type: "Quarterly Pest Control",
          date: "2025-06-15",
          technician: "Mike Johnson",
          satisfaction_score: 5,
          notes: "Summer treatment completed.",
          cost: 95
        },
        {
          type: "Quarterly Pest Control",
          date: "2025-03-10",
          technician: "Jennifer Lee",
          satisfaction_score: 5,
          notes: "Spring service.",
          cost: 95
        }
      ],
      current_plan: "Quarterly Pest Control Plan",
      upcoming_service: {
        type: "Quarterly Pest Control",
        scheduled_date: "2026-03-05"
      },
      customer_lifetime_value: "high",
      account_created: "2024-12-01",
      payment_status: "current",
      property_info: {
        type: "Single Family Home",
        year_built: 2010,
        size_sqft: 2600,
        lot_features: ["backs to woods", "creek nearby", "covered patio"]
      }
    }
  },
  {
    name: "Recent Upsell Already Sent",
    data: {
      event_type: "service_completed",
      customer: {
        id: "cust_008",
        first_name: "Lisa",
        last_name: "Nguyen",
        email: "lisa.nguyen@example.com",
        phone: "(555) 678-9012",
        address: {
          street: "445 Harbor View",
          city: "San Diego",
          state: "CA",
          zip: "92101"
        }
      },
      service_history: [
        {
          type: "General Pest Control",
          date: "2025-12-01",
          technician: "Tom Anderson",
          satisfaction_score: 5,
          notes: "Excellent service. Customer very happy. Property in great condition.",
          cost: 85
        },
        {
          type: "General Pest Control",
          date: "2025-09-05",
          technician: "Tom Anderson",
          satisfaction_score: 5,
          notes: "Routine treatment. No issues.",
          cost: 85
        },
        {
          type: "General Pest Control",
          date: "2025-06-01",
          technician: "Tom Anderson",
          satisfaction_score: 5,
          notes: "Summer service completed.",
          cost: 85
        },
        {
          type: "Initial Service",
          date: "2025-03-15",
          technician: "Mike Johnson",
          satisfaction_score: 5,
          notes: "New customer. Property assessment completed.",
          cost: 125
        }
      ],
      current_plan: "General Pest Control (one-time)",
      upcoming_service: {
        type: "General Pest Control",
        scheduled_date: "2026-03-01"
      },
      customer_lifetime_value: "medium",
      account_created: "2025-03-10",
      last_upsell_sent: "2025-11-18",
      payment_status: "current"
    }
  }
]
