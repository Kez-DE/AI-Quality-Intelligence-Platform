# AI Quality Intelligence Platform

Collects feedback about the service, classifies it with AI, and routes it to the internal teams that act on it.

## People and surfaces

**Customer**:
A person outside the company who reports Feedback through the Customer web. A Customer has no account.
_Avoid_: guest, public user, user, khách (for a logged-in role)

**Staff account**:
An account on the Staff web with the role admin, manager, or staff.
_Avoid_: user, member

**Pending account**:
An account on the Staff web that has no access until an admin grants it a Staff role. Only an admin creates accounts.
_Avoid_: guest, unapproved user

**Customer web**:
The separate website where a Customer submits Feedback and checks its status without logging in.
_Avoid_: public page, guest portal, /f

**Staff web**:
The internal website where Staff accounts review, route, and act on Feedback.
_Avoid_: the app, dashboard (for the whole site)

## Feedback

**Lookup code**:
The code a Customer receives after submitting Feedback, used to check its status on the Customer web.
_Avoid_: ticket id, tracking number, public ref

**Feedback status**:
What a Customer sees for a Lookup code: Received, Under review, or Reviewed. Reviewed means staff checked the AI classification, not that the underlying problem is fixed. A Customer never sees the AI labels themselves.
_Avoid_: resolved, closed, done
