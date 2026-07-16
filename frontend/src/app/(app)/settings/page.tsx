'use client'
import api from '@/lib/api'
import { useAuthStore } from '@/store/auth'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bell, CheckCircle, Copy, CreditCard, Key, Plus, Settings2, Trash2, X } from 'lucide-react'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'
import toast from 'react-hot-toast'

declare global {
  interface Window {
    Razorpay: new (opts: Record<string, unknown>) => { open: () => void }
  }
}

interface APIKey { id: string; name: string; key_prefix: string; last_used_at?: string; is_active: boolean; created_at: string }
interface UserSettings { ollama_url: string; ollama_model: string; grounding_threshold: number; faithfulness_alert_threshold: number; enable_email_alerts: boolean; slack_webhook_url?: string; slack_alert_enabled?: boolean }

const TABS = [
  { id: 'api-keys', label: 'API Keys', icon: Key },
  { id: 'ollama', label: 'Ollama Config', icon: Settings2 },
  { id: 'billing', label: 'Billing', icon: CreditCard },
  { id: 'alerts', label: 'Alerts', icon: Bell },
  { id: 'account', label: 'Account', icon: Settings2 },
]

function TabPanel({ active, id, children }: { active: string; id: string; children: React.ReactNode }) {
  return active === id ? <>{children}</> : null
}

function SettingsContent() {
  const searchParams = useSearchParams()
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') || 'api-keys')
  const { user, fetchMe } = useAuthStore()
  const queryClient = useQueryClient()

  // API Keys
  const [newKeyName, setNewKeyName] = useState('')
  const [createdKey, setCreatedKey] = useState<string | null>(null)
  const [showCreated, setShowCreated] = useState(false)

  // Ollama settings
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434')
  const [ollamaModel, setOllamaModel] = useState('llama3.2:3b')
  const [groundingThreshold, setGroundingThreshold] = useState(0.5)
  const [faithThreshold, setFaithThreshold] = useState(0.7)
  const [emailAlerts, setEmailAlerts] = useState(false)
  // Slack settings
  const [slackWebhookUrl, setSlackWebhookUrl] = useState('')
  const [slackAlertEnabled, setSlackAlertEnabled] = useState(false)

  // Account
  const [name, setName] = useState(user?.name || '')
  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')

  const { data: keys, isLoading: keysLoading } = useQuery<APIKey[]>({
    queryKey: ['api-keys'],
    queryFn: () => api.get('/keys').then(r => r.data),
  })

  const { data: settings } = useQuery<UserSettings>({
    queryKey: ['settings'],
    queryFn: () => api.get('/settings').then(r => r.data),
  })

  useEffect(() => {
    if (settings) {
      setOllamaUrl(settings.ollama_url)
      setOllamaModel(settings.ollama_model)
      setGroundingThreshold(settings.grounding_threshold)
      setFaithThreshold(settings.faithfulness_alert_threshold)
      setEmailAlerts(settings.enable_email_alerts)
      setSlackWebhookUrl(settings.slack_webhook_url || '')
      setSlackAlertEnabled(settings.slack_alert_enabled || false)
    }
  }, [settings])

  const { data: plans } = useQuery({
    queryKey: ['plans'],
    queryFn: () => api.get('/billing/plans').then(r => r.data),
  })

  const { data: usage } = useQuery({
    queryKey: ['billing-usage'],
    queryFn: () => api.get('/billing/usage').then(r => r.data),
  })

  const createKeyMutation = useMutation({
    mutationFn: () => api.post('/keys', { name: newKeyName }),
    onSuccess: (res) => {
      setCreatedKey(res.data.raw_key)
      setShowCreated(true)
      setNewKeyName('')
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
    },
    onError: () => toast.error('Failed to create key'),
  })

  const revokeKeyMutation = useMutation({
    mutationFn: (id: string) => api.delete(`/keys/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      toast.success('Key revoked')
    },
  })

  const saveSettingsMutation = useMutation({
    mutationFn: () => api.put('/settings', {
      ollama_url: ollamaUrl, ollama_model: ollamaModel,
      grounding_threshold: groundingThreshold,
      faithfulness_alert_threshold: faithThreshold,
      enable_email_alerts: emailAlerts,
      slack_webhook_url: slackWebhookUrl || null,
      slack_alert_enabled: slackAlertEnabled,
    }),
    onSuccess: () => toast.success('Settings saved'),
    onError: () => toast.error('Failed to save settings'),
  })

  const updateAccountMutation = useMutation({
    mutationFn: () => api.put('/auth/me', { name }),
    onSuccess: () => { fetchMe(); toast.success('Account updated') },
  })

  const changePasswordMutation = useMutation({
    mutationFn: () => api.post('/auth/change-password', { current_password: currentPwd, new_password: newPwd }),
    onSuccess: () => { setCurrentPwd(''); setNewPwd(''); toast.success('Password changed') },
    onError: (e: unknown) => toast.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed'),
  })

  const subscribeMutation = useMutation({
    mutationFn: (plan: string) => api.post('/billing/create-subscription', { plan }),
    onSuccess: (res) => {
      const { subscription_id, razorpay_key_id, customer_id } = res.data
      const script = document.createElement('script')
      script.src = 'https://checkout.razorpay.com/v1/checkout.js'
      script.onload = () => {
        const rzp = new window.Razorpay({
          key: razorpay_key_id,
          subscription_id,
          name: 'RAGInspector',
          description: 'RAGInspector Subscription',
          prefill: { email: user?.email, name: user?.name },
          handler: () => {
            toast.success('Subscription activated! Refreshing...')
            setTimeout(() => fetchMe(), 2000)
          },
          modal: { ondismiss: () => toast('Payment cancelled') },
        })
        rzp.open()
      }
      document.head.appendChild(script)
    },
    onError: (e: unknown) => toast.error((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Payment setup failed'),
  })

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => toast.success('Copied!'))
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-muted-foreground text-sm mt-1">Manage your account, API keys, and integrations</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar tabs */}
        <div className="w-44 shrink-0">
          <nav className="space-y-0.5">
            {TABS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeTab === id ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
                }`}
              >
                <Icon size={15} />
                {label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1">
          {/* API Keys Tab */}
          <TabPanel active={activeTab} id="api-keys">
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold text-foreground mb-1">API Keys</h2>
              <p className="text-sm text-muted-foreground mb-5">Use these keys to authenticate the SDK. Keys start with <code className="font-mono text-xs bg-muted px-1 py-0.5 rounded">ri-</code></p>

              {/* Created key banner */}
              {showCreated && createdKey && (
                <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-sm font-semibold text-green-700 flex items-center gap-1.5"><CheckCircle size={14} /> New key created — copy now</p>
                    <button onClick={() => setShowCreated(false)} className="text-green-600 hover:text-green-800"><X size={14} /></button>
                  </div>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-sm font-mono text-green-800 bg-green-100 px-3 py-2 rounded-lg break-all">{createdKey}</code>
                    <button onClick={() => copyToClipboard(createdKey)} className="shrink-0 text-green-700 hover:text-green-900 p-2 rounded-lg hover:bg-green-100 transition-colors">
                      <Copy size={15} />
                    </button>
                  </div>
                </div>
              )}

              {/* Create key form */}
              <div className="flex gap-2 mb-6">
                <input
                  value={newKeyName}
                  onChange={e => setNewKeyName(e.target.value)}
                  placeholder="Key name (e.g., Production)"
                  className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                />
                <button
                  onClick={() => createKeyMutation.mutate()}
                  disabled={!newKeyName || createKeyMutation.isPending}
                  className="flex items-center gap-1.5 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                >
                  <Plus size={14} />
                  Create
                </button>
              </div>

              {/* Keys list */}
              {keysLoading ? (
                <div className="space-y-2">{Array(2).fill(0).map((_, i) => <div key={i} className="skeleton h-14 rounded-lg" />)}</div>
              ) : !keys?.length ? (
                <p className="text-sm text-muted-foreground text-center py-6">No API keys yet</p>
              ) : (
                <div className="space-y-2">
                  {keys.map(k => (
                    <div key={k.id} className="flex items-center gap-3 bg-muted/30 border border-border rounded-xl px-4 py-3">
                      <Key size={15} className="text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground">{k.name}</p>
                        <p className="text-xs text-muted-foreground font-mono">{k.key_prefix}••••••••</p>
                      </div>
                      <p className="text-xs text-muted-foreground shrink-0">
                        {k.last_used_at ? `Used ${new Date(k.last_used_at).toLocaleDateString()}` : 'Never used'}
                      </p>
                      <button
                        onClick={() => {
                          if (confirm(`Revoke key "${k.name}"?`)) revokeKeyMutation.mutate(k.id)
                        }}
                        className="text-muted-foreground hover:text-destructive transition-colors p-1"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </TabPanel>

          {/* Ollama Config Tab */}
          <TabPanel active={activeTab} id="ollama">
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold text-foreground mb-1">AI Configuration</h2>
              <p className="text-sm text-muted-foreground mb-5">
                Configure LLM for RAGAS metric computation. Uses Hugging Face Inference API (free) if <code className="bg-muted px-1 rounded">HF_API_TOKEN</code> is set in .env, otherwise falls back to Ollama.
                <a href="https://huggingface.co/settings/tokens" target="_blank" className="text-primary hover:underline ml-1">Get free HF token →</a>
              </p>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Ollama Base URL</label>
                  <input value={ollamaUrl} onChange={e => setOllamaUrl(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                  <p className="text-xs text-muted-foreground mt-1">Default: http://localhost:11434 (or host.docker.internal:11434 from Docker)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">Model</label>
                  <input value={ollamaModel} onChange={e => setOllamaModel(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                  <p className="text-xs text-muted-foreground mt-1">Recommended: <code className="bg-muted px-1 rounded">llama3.2:3b</code> (fast) or <code className="bg-muted px-1 rounded">phi3:mini</code></p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Grounding Threshold: <span className="text-primary font-semibold">{groundingThreshold}</span>
                  </label>
                  <input type="range" min="0" max="1" step="0.05" value={groundingThreshold}
                    onChange={e => setGroundingThreshold(Number(e.target.value))}
                    className="w-full accent-primary" />
                  <p className="text-xs text-muted-foreground mt-1">NLI confidence score above which a sentence is considered grounded (0.5 recommended)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-foreground mb-1.5">
                    Faithfulness Alert Threshold: <span className="text-primary font-semibold">{faithThreshold}</span>
                  </label>
                  <input type="range" min="0" max="1" step="0.05" value={faithThreshold}
                    onChange={e => setFaithThreshold(Number(e.target.value))}
                    className="w-full accent-primary" />
                  <p className="text-xs text-muted-foreground mt-1">Queries below this faithfulness score are flagged</p>
                </div>
                <div className="flex items-center gap-3">
                  <input type="checkbox" id="emailAlerts" checked={emailAlerts} onChange={e => setEmailAlerts(e.target.checked)} className="accent-primary" />
                  <label htmlFor="emailAlerts" className="text-sm text-foreground">Enable email alerts for low faithfulness scores</label>
                </div>
                <button onClick={() => saveSettingsMutation.mutate()} disabled={saveSettingsMutation.isPending}
                  className="bg-primary text-primary-foreground px-5 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                  {saveSettingsMutation.isPending ? 'Saving...' : 'Save settings'}
                </button>
              </div>
            </div>
          </TabPanel>

          {/* Billing Tab */}
          <TabPanel active={activeTab} id="billing">
            <div className="bg-card border border-border rounded-xl p-5 mb-4">
              <h2 className="font-semibold text-foreground mb-1">Current Plan</h2>
              <div className="flex items-center gap-3 mt-3">
                <div className="w-10 h-10 bg-primary/10 rounded-xl flex items-center justify-center">
                  <CreditCard size={18} className="text-primary" />
                </div>
                <div>
                  <p className="font-semibold text-foreground capitalize">{user?.subscription_plan} Plan</p>
                  <p className="text-xs text-muted-foreground">
                    {user?.subscription_status ? `Status: ${user.subscription_status}` : 'No active subscription'}
                  </p>
                </div>
                <div className="ml-auto text-right">
                  <p className="text-sm text-muted-foreground">Traces this month</p>
                  <p className="font-semibold text-foreground">
                    {(usage?.traces_used ?? user?.traces_this_month ?? 0).toLocaleString()}
                    {usage?.traces_limit != null ? ` / ${usage.traces_limit.toLocaleString()}` : ''}
                  </p>
                  {usage?.traces_remaining != null && (
                    <p className="text-xs text-muted-foreground">{usage.traces_remaining.toLocaleString()} remaining</p>
                  )}
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {plans?.plans?.map((plan: {
                id: string; name: string; price_inr: number; price_usd: number; price_label?: string;
                traces_per_month: number; features: string[];
              }) => (
                <div key={plan.id} className={`border rounded-xl p-5 ${user?.subscription_plan === plan.id.replace('_monthly', '') ? 'border-primary bg-primary/5' : 'border-border bg-card'}`}>
                  <h3 className="font-bold text-foreground mb-1">{plan.name}</h3>
                  <div className="mb-4">
                    <p className="text-lg font-bold text-foreground">{plan.price_label || `₹${plan.price_inr.toLocaleString()}/mo · $${plan.price_usd}/mo`}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">INR · USD</p>
                  </div>
                  <ul className="space-y-1.5 mb-5 text-sm">
                    {plan.features.map((f: string) => (
                      <li key={f} className="flex items-start gap-1.5 text-muted-foreground">
                        <span className="text-primary mt-0.5">✓</span> {f}
                      </li>
                    ))}
                  </ul>
                  {plan.id === 'free' ? (
                    <div className="text-center text-xs text-muted-foreground py-2">Current free plan — 100 queries/mo</div>
                  ) : (
                    <button
                      onClick={() => subscribeMutation.mutate(plan.id)}
                      disabled={subscribeMutation.isPending || user?.subscription_plan === plan.id.replace('_monthly', '')}
                      className="w-full bg-primary text-primary-foreground py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors"
                    >
                      {user?.subscription_plan === plan.id.replace('_monthly', '') ? 'Current plan' : `Upgrade to ${plan.name}`}
                    </button>
                  )}
                </div>
              ))}
            </div>

            {user?.subscription_plan !== 'free' && (
              <div className="mt-4 text-center">
                <button
                  onClick={async () => {
                    if (!confirm('Cancel subscription at end of billing period?')) return
                    try {
                      await api.post('/billing/cancel-subscription')
                      toast.success('Subscription will cancel at period end')
                      fetchMe()
                    } catch {
                      toast.error('Cancellation failed')
                    }
                  }}
                  className="text-sm text-muted-foreground hover:text-destructive transition-colors"
                >
                  Cancel subscription
                </button>
              </div>
            )}
          </TabPanel>

          {/* Alerts Tab */}
          <TabPanel active={activeTab} id="alerts">
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold text-foreground mb-1">Alert Configuration</h2>
              <p className="text-sm text-muted-foreground mb-5">Get notified when RAG quality drops below thresholds.</p>
              <div className="space-y-5">
                {/* Email alerts */}
                <div className="flex items-center justify-between p-4 bg-muted/30 rounded-xl border border-border">
                  <div>
                    <p className="text-sm font-medium text-foreground">Faithfulness Alert (Email)</p>
                    <p className="text-xs text-muted-foreground">Notify when faithfulness drops below {faithThreshold * 100}%</p>
                  </div>
                  <input type="checkbox" checked={emailAlerts} onChange={e => setEmailAlerts(e.target.checked)} className="accent-primary w-4 h-4" />
                </div>
                <p className="text-xs text-muted-foreground -mt-3">Email alerts require SMTP configuration in your .env file.</p>

                {/* Slack alerts (NEW: PRD v2.0) */}
                <div className="border-t border-border pt-5">
                  <h3 className="text-sm font-semibold text-foreground mb-1">Slack Alerts</h3>
                  <p className="text-xs text-muted-foreground mb-3">
                    Get notified when hallucination rate spikes. Uses Slack Incoming Webhooks (free).
                    <a href="https://slack.com/apps/A0F7XDUAZ-incoming-webhooks" target="_blank" className="text-primary hover:underline ml-1">Create webhook →</a>
                  </p>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-sm font-medium text-foreground mb-1.5">Slack Webhook URL</label>
                      <input value={slackWebhookUrl} onChange={e => setSlackWebhookUrl(e.target.value)}
                        placeholder="https://hooks.slack.com/services/..."
                        className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring font-mono" />
                    </div>
                    <div className="flex items-center gap-3">
                      <input type="checkbox" id="slackAlerts" checked={slackAlertEnabled} onChange={e => setSlackAlertEnabled(e.target.checked)} className="accent-primary" />
                      <label htmlFor="slackAlerts" className="text-sm text-foreground">Enable Slack hallucination spike alerts</label>
                    </div>
                  </div>
                </div>

                <button onClick={() => saveSettingsMutation.mutate()} disabled={saveSettingsMutation.isPending}
                  className="bg-primary text-primary-foreground px-5 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                  Save
                </button>
              </div>
            </div>
          </TabPanel>

          {/* Account Tab */}
          <TabPanel active={activeTab} id="account">
            <div className="space-y-4">
              <div className="bg-card border border-border rounded-xl p-5">
                <h2 className="font-semibold text-foreground mb-4">Profile</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">Display name</label>
                    <input value={name} onChange={e => setName(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">Email</label>
                    <input value={user?.email || ''} disabled
                      className="w-full bg-muted border border-border rounded-lg px-3 py-2 text-sm text-muted-foreground" />
                  </div>
                  <button onClick={() => updateAccountMutation.mutate()} disabled={updateAccountMutation.isPending}
                    className="bg-primary text-primary-foreground px-5 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                    Save profile
                  </button>
                </div>
              </div>

              <div className="bg-card border border-border rounded-xl p-5">
                <h2 className="font-semibold text-foreground mb-4">Change Password</h2>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">Current password</label>
                    <input type="password" value={currentPwd} onChange={e => setCurrentPwd(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-foreground mb-1.5">New password</label>
                    <input type="password" value={newPwd} onChange={e => setNewPwd(e.target.value)}
                      className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
                  </div>
                  <button onClick={() => changePasswordMutation.mutate()} disabled={!currentPwd || !newPwd || changePasswordMutation.isPending}
                    className="bg-primary text-primary-foreground px-5 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
                    {changePasswordMutation.isPending ? 'Updating...' : 'Update password'}
                  </button>
                </div>
              </div>
            </div>
          </TabPanel>
        </div>
      </div>
    </div>
  )
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="p-6 max-w-4xl mx-auto"><div className="skeleton h-96 rounded-xl" /></div>}>
      <SettingsContent />
    </Suspense>
  )
}
