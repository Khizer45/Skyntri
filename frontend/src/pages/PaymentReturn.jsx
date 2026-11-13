import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Card from '../components/Card.jsx'
import { money } from '../components/ui.jsx'
import DashboardLayout from '../layouts/DashboardLayout.jsx'
import * as api from '../services/api.js'

// The customer lands here after paying (or cancelling) on Safepay, Stripe or PayPal.
// The server asks the provider for the real result.
export default function PaymentReturn() {
  const [params] = useSearchParams()
  const paymentId = params.get('payment')
  const cancelled = params.get('cancelled') === '1'
  const [payment, setPayment] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!paymentId) {
      setError('This payment link is not complete.')
      return
    }
    const action = cancelled ? api.cancelPayment(paymentId) : api.confirmPayment(paymentId)
    action.then(setPayment).catch((err) => setError(err.message))
  }, [paymentId, cancelled])

  const back = payment?.purpose === 'appointment'
    ? { to: `/appointments/${payment.reference_id}`, label: 'Back to the appointment' }
    : { to: '/orders', label: 'Back to my orders' }

  let title = 'Checking your payment…'
  let text = 'Please wait a moment.'
  if (error) {
    title = 'We could not check this payment'
    text = error
  } else if (payment?.status === 'succeeded') {
    title = 'Payment received'
    text = `Thank you. ${money(payment.amount, payment.currency)} was paid.`
  } else if (payment) {
    title = cancelled || payment.status === 'cancelled' ? 'Payment cancelled' : 'Payment not completed'
    text = 'No money was taken. You can try again or choose another way to pay.'
  }

  return (
    <DashboardLayout title="Payment" width="md">
      <Card className="p-8 text-center">
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-white">{title}</h2>
        <p className="muted mt-2 text-sm">{text}</p>
        {(payment || error) && (
          <Link to={payment ? back.to : '/dashboard'} className="link mt-5 inline-block text-sm">
            {payment ? back.label : 'Go to home'}
          </Link>
        )}
      </Card>
    </DashboardLayout>
  )
}
