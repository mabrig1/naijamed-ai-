# MediNaija USSD fallback contract

The app must not claim a live short code until a Nigerian USSD aggregator has provisioned one.

## Intended menu

1. Refill medicine
2. Pay / renew plan
3. Check refill or order status
4. Speak with an agent

The aggregator should POST session data to a dedicated webhook using a signed request. Phone number is the primary identifier and must be normalized to +234 format before lookup.

## Production rule

Do not hard-code *737# as MediNaija's short code. *737# is a familiar Nigerian bank-style interaction pattern; the production MediNaija code must be the exact code assigned by the selected aggregator.

## SMS mirror

Every USSD action must have an SMS confirmation through Termii. Sensitive health details should not be placed in SMS; use short operational messages such as refill due, order received, payment pending or agent callback requested.
