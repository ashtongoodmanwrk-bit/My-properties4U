import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from './api'
import type { RentCharge } from './types'

export default function PayButton({ charge }: { charge: RentCharge }) {
  const queryClient = useQueryClient()
  const [amount, setAmount] = useState(charge.amount)
  // One key per payment attempt. It is kept on failure so a retry is safe,
  // and cleared after success or when the amount changes.
  const keyRef = useRef<string | null>(null)

  const pay = useMutation({
    mutationFn: () => {
      if (keyRef.current === null) keyRef.current = crypto.randomUUID()
      return api.pay(charge.id, amount, keyRef.current)
    },
    onSuccess: () => {
      keyRef.current = null
      void queryClient.invalidateQueries({ queryKey: ['charges'] })
    },
  })

  function onAmountChange(value: string) {
    setAmount(value)
    keyRef.current = null
    pay.reset()
  }

  return (
    <div>
      <label className="sr-only" htmlFor={`amount-${charge.id}`}>
        Amount to pay for the charge due {charge.due_date}
      </label>
      <input
        id={`amount-${charge.id}`}
        type="number"
        min="0.01"
        step="0.01"
        value={amount}
        onChange={(e) => onAmountChange(e.target.value)}
        disabled={pay.isPending}
        style={{ width: '6rem', marginRight: '0.5rem' }}
      />
      <button type="button" onClick={() => pay.mutate()} disabled={pay.isPending || amount === ''}>
        {pay.isPending ? 'Paying...' : 'Pay rent'}
      </button>
      {pay.isError && (
        <p role="alert" className="error">
          {pay.error.message}
        </p>
      )}
    </div>
  )
}
