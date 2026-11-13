import { CreditCard, Wallet } from 'lucide-react'
import { useEffect, useState } from 'react'
import * as api from '../services/api.js'
import Button from './Button.jsx'
import { Alert, money } from './ui.jsx'

const ICONS = { stripe: CreditCard, safepay: CreditCard, paypal: Wallet }

/**
 * Pay an order or an appointment online. Lists the methods the server has
 * set up, then sends the browser to the provider's own payment page.
 */
export default function PaymentOptions({ purpose, referenceId, offlineLabel }) {
  const [info, setInfo] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => {
    let active = true
    setInfo(null)
    api
      .getPaymentMethods(purpose, referenceId)
      .then((data) => active && setInfo(data))
      .catch((err) => active && setError(err.message))
    return () => {
      active = false
    }
  }, [purpose, referenceId])

  const pay = async (provider) => {
    setBusy(provider)
    setError('')
    try {
      const { redirect_url: url } = await api.startCheckout(purpose, referenceId, provider)
      if (!api.isSafePaymentUrl(url)) throw new Error('The payment page address was not recognised.')
      window.location.assign(url)
    } catch (err) {
      setError(err.message || 'The payment could not be started.')
      setBusy('')
    }
  }

  if (error && !info) return <Alert>{error}</Alert>
  if (!info) return <p className="muted text-sm">Loading payment options…</p>

  const available = info.methods.filter((m) => m.available)

  return (
    <div className="space-y-3">
      {error && <Alert>{error}</Alert>}
      {available.length === 0 ? (
        <Alert tone="neutral">
          Online payment is not set up yet.{offlineLabel ? ` You can ${offlineLabel}.` : ''}
        </Alert>
      ) : (
        <>
          <div className="flex flex-wrap gap-2">
            {available.map((method) => {
              const converted = method.currency !== info.currency
              return (
                <Button
                  key={method.id}
                  variant={method.label === 'Card' ? 'primary' : 'outline'}
                  icon={ICONS[method.id]}
                  loading={busy === method.id}
                  disabled={Boolean(busy)}
                  onClick={() => pay(method.id)}
                >
                  Pay with {method.label}
                  {converted && ` (${money(method.amount, method.currency)})`}
                </Button>
              )
            })}
          </div>
          {available.some((m) => m.test_mode) && <p className="muted text-xs">Test mode: no real money is taken.</p>}
          <p className="muted text-xs">
            You pay on the payment company's secure page. Skyntri never sees your card number.
            {offlineLabel ? ` You can also ${offlineLabel}.` : ''}
          </p>
        </>
      )}
    </div>
  )
}
