# Cricket Connect platform guidance

## Finding sessions

Sign in to Cricket Connect and use Find Sessions to search sessions. Session search supports sport and city filters. Search results include the session title, sport, provider's business name, venue city, start/end times, capacity, and description when provided. A session must be created by a provider to appear in the database-backed search. Current sessions and venue records are shown from the live application database by the chat assistant when asked.

## Booking sessions

Only a player account can create a booking. A player selects a session and submits a booking request; its initial status is PENDING. The application checks session capacity and prevents the same player from having multiple non-cancelled bookings for one session. PENDING and CONFIRMED bookings count toward session capacity. A provider can manage bookings associated with their own sessions. The application does not currently provide a player booking-cancellation endpoint. The chatbot cannot create, change, or cancel bookings.

## Venues and facilities

The venue record contains a name, address, city, and optional latitude and longitude. The current database schema does not store venue facilities or prices. The chat assistant must not infer these details; contact the venue/provider for information not listed in the record.

## Provider sessions

An account with the PROVIDER role must create a provider profile before managing venues or sessions. Providers can create venues and create, update, or delete sessions for their own profile. A session has a title, optional description, sport, venue, start and end times, and capacity. A provider can only attach a venue owned by that provider.

## Accounts and privacy

Session discovery and venue browsing require authentication. Player booking routes are restricted to the authenticated player, and provider management routes are restricted to providers and their own records. The chat assistant only uses public session and venue fields, plus an aggregate remaining-place count. It does not retrieve or disclose user profiles, email addresses, or individual booking records.
