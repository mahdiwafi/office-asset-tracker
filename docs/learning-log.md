# Learning log

First-person notes on what each checkpoint actually taught me. Written
after the fact, in my own words — the point is to be able to *explain*
these under questioning, not just to have done them.

## 2026-08-22 — Day 5: the three-walled first login

The app was deployed: two Azure Container Apps, images in GHCR, CI green,
the API healthy. Then I spent the better part of a day trying to sign in
through the browser. Three separate walls, each one a different layer, and
each one only visible after the previous one was removed.

### Wall 1 — the account itself (the "We couldn't sign you in" loop)

**Symptom:** the app redirected to Microsoft, and the sign-in page looped
between `authorize` and `reprocess` with a generic "We couldn't sign you
in. Please try again." — no error code, no details.

**What I tried first (and why it was the wrong layer):** browser fixes —
incognito, another window, clearing cookies. All useless, which was the
first real clue: a config problem wouldn't care about the browser.

**What actually worked:** we replayed the exact authorize request the app
was making (curl, with the real PKCE challenge from the URL bar) and got a
clean sign-in page back — *no error*. That proved the request, the app
registration, the redirect URI and the scope were all valid. So the
failure was inside Entra's session handling, and the error page finally
named it: the account shown was `teiiforbat@outlook.com` — a **consumer
Microsoft account**. My tenant was created from a personal Outlook
account, and that consumer identity can sign into the Azure portal (it
gets a special path there) but cannot complete a normal OIDC sign-in
against the workforce directory. The tenant's user list said `Users: 1` —
there was literally no directory user that could sign in. **Fix:** create
a real user (`wafi@teiiforbatoutlook.onmicrosoft.com`), sign in with it.

**Lesson:** the browser session is the *last* thing to blame, not the
first. The bisect that worked was replaying the request server-side to
prove the config layer, then reading the error page for the identity it
named. Also: a free-trial Azure tenant is founded on a consumer account,
and that account is not a directory user — know which identity your app
expects before debugging anything else.

### Wall 2 — Web platform vs SPA platform (AADSTS9002326)

**Symptom:** after the new user worked, sign-in succeeded but the app
bounced straight back to the login page. Console showed the token
exchange POST failing with **400**.

**The trap:** at every earlier stage the request was valid — authorize
passed, sign-in passed, the code came back to the app. Only the final
leg, the code-for-token exchange, failed, and only in a browser. A
server-side replay could never see it: the failure was a *cross-origin*
check.

**Root cause:** I had registered the redirect URI under the **Web**
platform of the app registration. That makes Entra treat the app as a
confidential client. But MSAL.js is a public client doing the SPA flow
(PKCE, code exchanged from the browser origin). Entra's token endpoint
answered `AADSTS9002326: Cross-origin token redemption is permitted only
for the 'Single-Page Application' client-type.` **Fix:** add the same
redirect URIs under a **Single-page application** platform instead.

**Lesson:** the platform type in the app registration is not decoration —
it selects the client type, and the client type decides which flows the
token endpoint will accept. Web ≠ SPA. This is a one-word config error
whose failure only surfaces at the last hop, in a browser, with a 400
that a scripted test would miss.

### The method, generalised

1. Prove the request (replay it) before debugging the environment.
2. Prove the config layer before blaming the browser.
3. When the failure needs a browser to reproduce, the console and the
   Network tab's *response body* are the evidence — the error JSON named
   the exact AADSTS code.
4. Each wall was invisible until the previous one fell: consumer account
   → directory user → then the platform mismatch surfaced. Debug the
   layers in order, and the error pages will keep naming the next one.

### Interview takeaway

The sequence I can now tell from memory, with the receipts: replayable
authorize request, tenant with one consumer account, `Users: 1`, and the
9002326 response body that named the fix. That is a complete story about
how Entra classifies clients — worth more than a paragraph of theory.
