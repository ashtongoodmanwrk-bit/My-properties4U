const gbp = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'GBP' })
const gbpWhole = new Intl.NumberFormat('en-GB', {
  style: 'currency',
  currency: 'GBP',
  maximumFractionDigits: 0,
})
const dateFmt = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})

export function money(value: string | number): string {
  return gbp.format(Number(value))
}

export function moneyWhole(value: string | number): string {
  return gbpWhole.format(Number(value))
}

export function formatDate(iso: string): string {
  return dateFmt.format(new Date(iso))
}
