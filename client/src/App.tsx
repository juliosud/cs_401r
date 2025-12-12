import { useState, useEffect } from 'react'
import { 
  Send, 
  Mail, 
  CheckCircle, 
  XCircle, 
  Clock, 
  RefreshCw,
  User,
  MessageSquare,
  Star,
  AlertCircle,
  Loader2
} from 'lucide-react'
import axios from 'axios'
import './App.css'
import { ReferralMessage, Status, ServiceCatalog } from './types'
import { mockCustomers } from './mockData'


function App() {
  const webhookUrl = import.meta.env.VITE_WEBHOOK_URL || 'http://localhost:8000/webhook'
  const [selectedCustomer, setSelectedCustomer] = useState(0)
  const [loading, setLoading] = useState(false)
  const [fetchingMessages, setFetchingMessages] = useState(true)
  const [messages, setMessages] = useState<ReferralMessage[]>([])
  const [showHistory, setShowHistory] = useState(false)
  const [showCustomerDetails, setShowCustomerDetails] = useState(false)
  const [showServiceCatalog, setShowServiceCatalog] = useState(false)
  const [serviceCatalog, setServiceCatalog] = useState<ServiceCatalog | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [serverUrl] = useState('http://localhost:8000')

  // Fetch messages from backend
  const fetchMessages = async (showLoading = false) => {
    if (showLoading) setFetchingMessages(true)
    try {
      const response = await axios.get<ReferralMessage[]>(`${serverUrl}/messages`)
      setMessages(response.data)
    } catch (err) {
      console.error('Error fetching messages:', err)
    } finally {
      if (showLoading) setFetchingMessages(false)
    }
  }

  // Fetch service catalog from backend
  const fetchServiceCatalog = async () => {
    try {
      const response = await axios.get<ServiceCatalog>(`${serverUrl}/service-catalog`)
      setServiceCatalog(response.data)
    } catch (err) {
      console.error('Error fetching service catalog:', err)
    }
  }

  useEffect(() => {
    fetchMessages(true)
    fetchServiceCatalog()
    // Poll for new messages every 5 seconds
    const interval = setInterval(() => fetchMessages(false), 5000)
    return () => clearInterval(interval)
  }, [serverUrl])

  const sendWebhook = async () => {
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      // Send webhook directly to AWS
      await axios.post(webhookUrl, mockCustomers[selectedCustomer].data)
      
      setSuccess(`Message generation in progress...`)
      
      // Wait for processing and fetch messages
      setTimeout(() => {
        fetchMessages(false)
        setLoading(false)
        setSuccess('Message processed! Check "All Message History" below.')
      }, 12000)
      
    } catch (err: any) {
      setError(err.response?.data?.message || err.message || 'Failed to send webhook')
      setLoading(false)
    }
  }

  const getStatusIcon = (status: Status) => {
    switch (status) {
      case 'approved':
        return <CheckCircle className="status-icon" />
      case 'rejected':
        return <XCircle className="status-icon" />
      default:
        return <Clock className="status-icon" />
    }
  }


  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">
              <MessageSquare size={28} strokeWidth={2.5} />
            </div>
            <div className="logo-text">
              <h1>Upsell Pro</h1>
              <p className="tagline">AI-Powered Service Upsell Generator</p>
            </div>
          </div>
        </div>
      </header>

      <main className="main">
        <div className="container">
          {/* Send Webhook Section */}
          <section className="card">
            <h2 className="card-title">
              <Send size={20} />
              Generate Message
            </h2>

            <div className="form-group">
              <label>Customer Scenario</label>
              <select
                value={selectedCustomer}
                onChange={(e) => setSelectedCustomer(Number(e.target.value))}
                className="select"
              >
                {mockCustomers.map((customer, idx) => (
                  <option key={idx} value={idx}>
                    {customer.name} - {customer.data.customer.first_name} {customer.data.customer.last_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="customer-preview">
              <div 
                className="customer-preview-header" 
                onClick={() => setShowCustomerDetails(!showCustomerDetails)}
              >
                <h4>Customer Details</h4>
                <button className="button secondary small">
                  {showCustomerDetails ? 'Hide Details' : 'Show Details'}
                </button>
              </div>
              
              {showCustomerDetails && (
                <div className="customer-info-expanded">
                  <div className="info-section">
                    <h5>Contact Information</h5>
                    <div className="info-row">
                      <User size={16} />
                      <span><strong>Name:</strong> {mockCustomers[selectedCustomer].data.customer.first_name} {mockCustomers[selectedCustomer].data.customer.last_name}</span>
                    </div>
                    <div className="info-row">
                      <Mail size={16} />
                      <span><strong>Email:</strong> {mockCustomers[selectedCustomer].data.customer.email}</span>
                    </div>
                    <div className="info-row">
                      <User size={16} />
                      <span><strong>Phone:</strong> {mockCustomers[selectedCustomer].data.customer.phone}</span>
                    </div>
                    <div className="info-row">
                      <User size={16} />
                      <span><strong>Address:</strong> {mockCustomers[selectedCustomer].data.customer.address.street}, {mockCustomers[selectedCustomer].data.customer.address.city}, {mockCustomers[selectedCustomer].data.customer.address.state} {mockCustomers[selectedCustomer].data.customer.address.zip}</span>
                    </div>
                  </div>

                  <div className="info-section">
                    <h5>Service History ({mockCustomers[selectedCustomer].data.service_history.length} services)</h5>
                    {mockCustomers[selectedCustomer].data.service_history.slice(0, 3).map((service, idx) => (
                      <div key={idx} className="service-history-item">
                        <div className="info-row">
                          <MessageSquare size={16} />
                          <span><strong>{service.type}</strong> - {service.date}</span>
                        </div>
                        <div className="info-row">
                          <User size={16} />
                          <span>Technician: {service.technician}</span>
                        </div>
                        <div className="info-row">
                          <Star size={16} />
                          <span>Satisfaction: {service.satisfaction_score}/5</span>
                        </div>
                        {service.notes && (
                          <div className="info-row notes">
                            <AlertCircle size={16} />
                            <span>{service.notes}</span>
                          </div>
                        )}
                      </div>
                    ))}
                    {mockCustomers[selectedCustomer].data.service_history.length > 3 && (
                      <div className="info-row">
                        <span style={{color: '#9ca3af', fontStyle: 'italic'}}>
                          + {mockCustomers[selectedCustomer].data.service_history.length - 3} more services
                        </span>
                      </div>
                    )}
                  </div>

                  <div className="info-section">
                    <h5>Account Information</h5>
                    <div className="info-row">
                      <Clock size={16} />
                      <span><strong>Customer Since:</strong> {mockCustomers[selectedCustomer].data.account_created}</span>
                    </div>
                    {mockCustomers[selectedCustomer].data.current_plan && (
                      <div className="info-row">
                        <CheckCircle size={16} />
                        <span><strong>Current Plan:</strong> {mockCustomers[selectedCustomer].data.current_plan}</span>
                      </div>
                    )}
                    <div className="info-row">
                      <Star size={16} />
                      <span><strong>Total Services:</strong> {mockCustomers[selectedCustomer].data.service_history.length}</span>
                    </div>
                    <div className="info-row">
                      <MessageSquare size={16} />
                      <span><strong>Lifetime Value:</strong> {mockCustomers[selectedCustomer].data.customer_lifetime_value}</span>
                    </div>
                    <div className="info-row">
                      <CheckCircle size={16} />
                      <span><strong>Payment Status:</strong> {mockCustomers[selectedCustomer].data.payment_status}</span>
                    </div>
                    {mockCustomers[selectedCustomer].data.upcoming_service && (
                      <div className="info-row">
                        <Clock size={16} />
                        <span><strong>Next Service:</strong> {mockCustomers[selectedCustomer].data.upcoming_service.type} on {mockCustomers[selectedCustomer].data.upcoming_service.scheduled_date}</span>
                      </div>
                    )}
                    {mockCustomers[selectedCustomer].data.last_upsell_sent && (
                      <div className="info-row">
                        <AlertCircle size={16} />
                        <span><strong>Last Upsell Sent:</strong> {mockCustomers[selectedCustomer].data.last_upsell_sent}</span>
                      </div>
                    )}
                  </div>

                  {mockCustomers[selectedCustomer].data.property_info && (
                    <div className="info-section">
                      <h5>Property Information</h5>
                      <div className="info-row">
                        <MessageSquare size={16} />
                        <span><strong>Type:</strong> {mockCustomers[selectedCustomer].data.property_info.type}</span>
                      </div>
                      {mockCustomers[selectedCustomer].data.property_info.year_built && (
                        <div className="info-row">
                          <Clock size={16} />
                          <span><strong>Built:</strong> {mockCustomers[selectedCustomer].data.property_info.year_built}</span>
                        </div>
                      )}
                      {mockCustomers[selectedCustomer].data.property_info.size_sqft && (
                        <div className="info-row">
                          <Star size={16} />
                          <span><strong>Size:</strong> {mockCustomers[selectedCustomer].data.property_info.size_sqft.toLocaleString()} sq ft</span>
                        </div>
                      )}
                      {mockCustomers[selectedCustomer].data.property_info.lot_features && mockCustomers[selectedCustomer].data.property_info.lot_features.length > 0 && (
                        <div className="info-row notes">
                          <AlertCircle size={16} />
                          <span><strong>Features:</strong> {mockCustomers[selectedCustomer].data.property_info.lot_features.join(', ')}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>

            <button
              onClick={sendWebhook}
              disabled={loading}
              className="button primary"
            >
              {loading ? (
                <>
                  <Loader2 size={20} className="spin" />
                  Generating Message...
                </>
              ) : (
                <>
                  <Send size={20} />
                  Generate Message
                </>
              )}
            </button>

            {error && (
              <div className="alert error">
                <AlertCircle size={20} />
                {error}
              </div>
            )}

            {success && (
              <div className="alert success">
                <CheckCircle size={20} />
                {success}
              </div>
            )}
          </section>

          {/* Service Catalog Section */}
          <section className="card">
            <div className="card-header clickable" onClick={() => setShowServiceCatalog(!showServiceCatalog)}>
              <h2 className="card-title">
                <MessageSquare size={20} />
                Service Catalog
              </h2>
              <button className="button secondary small">
                {showServiceCatalog ? 'Hide' : 'Show'}
              </button>
            </div>

            {showServiceCatalog && serviceCatalog && (
              <div className="service-catalog">
                {/* Preventive Services */}
                <div className="service-category">
                  <h3>Preventive Services</h3>
                  <div className="service-grid">
                    {serviceCatalog.preventive_services?.map((service, idx) => (
                      <div key={idx} className="service-item">
                        <h4>{service.name}</h4>
                        <p className="service-description">{service.description}</p>
                        <div className="service-detail">
                          <strong>Ideal For:</strong> {service.ideal_for}
                        </div>
                        <div className="service-detail">
                          <strong>Benefits:</strong>
                          <ul>
                            {service.benefits.map((benefit, bIdx) => (
                              <li key={bIdx}>{benefit}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="service-triggers">
                          <strong>Upsell Triggers:</strong> {service.upsell_triggers.join(', ')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Specialized Treatments */}
                <div className="service-category">
                  <h3>Specialized Treatments</h3>
                  <div className="service-grid">
                    {serviceCatalog.specialized_treatments?.map((service, idx) => (
                      <div key={idx} className="service-item">
                        <h4>{service.name}</h4>
                        <p className="service-description">{service.description}</p>
                        <div className="service-detail">
                          <strong>Ideal For:</strong> {service.ideal_for}
                        </div>
                        <div className="service-detail">
                          <strong>Benefits:</strong>
                          <ul>
                            {service.benefits.map((benefit, bIdx) => (
                              <li key={bIdx}>{benefit}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="service-triggers">
                          <strong>Upsell Triggers:</strong> {service.upsell_triggers.join(', ')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Add-on Services */}
                <div className="service-category">
                  <h3>Add-on Services</h3>
                  <div className="service-grid">
                    {serviceCatalog.add_on_services?.map((service, idx) => (
                      <div key={idx} className="service-item">
                        <h4>{service.name}</h4>
                        <p className="service-description">{service.description}</p>
                        <div className="service-detail">
                          <strong>Ideal For:</strong> {service.ideal_for}
                        </div>
                        <div className="service-detail">
                          <strong>Benefits:</strong>
                          <ul>
                            {service.benefits.map((benefit, bIdx) => (
                              <li key={bIdx}>{benefit}</li>
                            ))}
                          </ul>
                        </div>
                        <div className="service-triggers">
                          <strong>Upsell Triggers:</strong> {service.upsell_triggers.join(', ')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </section>

          {/* All Messages History Section */}
          {messages.length > 0 && (
            <section className="card">
              <div className="card-header clickable" onClick={() => setShowHistory(!showHistory)}>
                <h2 className="card-title">
                  <Mail size={20} />
                  All Message History ({messages.length})
                </h2>
                <button className="button secondary small">
                  {showHistory ? 'Hide' : 'Show'}
                </button>
              </div>

              {showHistory && (
                <div className="messages-list">
                  {messages.map((message, idx) => (
                    <div key={idx} className={`message-card ${message.status}`}>
                      <div className="message-header">
                        <div className="message-title">
                          <User size={18} />
                          <span>{message.customerName}</span>
                          <span className="email">{message.customerEmail}</span>
                        </div>
                        <div className={`message-status ${message.status}`}>
                          {getStatusIcon(message.status)}
                          <span>{message.status}</span>
                        </div>
                      </div>

                      <div className="message-meta">
                        <div className="meta-item">
                          <Star size={16} />
                          <span>Score: {message.llmJudgeScore}/10</span>
                        </div>
                        <div className="meta-item">
                          <Clock size={16} />
                          <span>{new Date(message.createdAt).toLocaleString()}</span>
                        </div>
                        {message.retryCount > 0 && (
                          <div className="meta-item">
                            <RefreshCw size={16} />
                            <span>Retries: {message.retryCount}</span>
                          </div>
                        )}
                      </div>

                      {message.emailSubject && (
                        <div className="message-subject">
                          <strong>Subject:</strong> {message.emailSubject}
                        </div>
                      )}

                      <div className="message-content">
                        {message.emailContent || 'No content available'}
                      </div>

                      {message.status === 'rejected' && (
                        <div className="llm-decision-box rejection">
                          <div className="decision-header">
                            <AlertCircle size={20} />
                            <strong>AI Judge Decision: Message Not Sent</strong>
                          </div>
                          {message.rejectionReason && message.rejectionReason !== 'N/A' && (
                            <div className="rejection-category">
                              <strong>Rejection Category:</strong> {
                                message.rejectionReason === 'appropriateness' ? 'Customer Appropriateness' :
                                message.rejectionReason === 'service_validity' ? 'Service Not Valid' :
                                message.rejectionReason === 'brand' ? 'Brand Guidelines' :
                                message.rejectionReason
                              }
                            </div>
                          )}
                          <div className="decision-reasoning">
                            <strong>Reasoning:</strong> {message.judgeFeedback}
                          </div>
                          <div className="judge-score">
                            <Star size={16} />
                            <span>Quality Score: {message.llmJudgeScore}/10</span>
                          </div>
                        </div>
                      )}
                      
                      {message.status === 'approved' && message.judgeFeedback && (
                        <div className="llm-decision-box approved">
                          <div className="decision-header">
                            <CheckCircle size={18} />
                            <strong>AI Judge Decision: Approved for Sending</strong>
                          </div>
                          <div className="decision-reasoning">
                            {message.judgeFeedback}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>
          )}

          {/* Empty State */}
          {messages.length === 0 && !fetchingMessages && (
            <section className="card">
              <div className="empty-state">
                <Mail size={48} />
                <p>No messages yet. Generate your first message above!</p>
              </div>
            </section>
          )}
        </div>
      </main>
    </div>
  )
}

export default App

