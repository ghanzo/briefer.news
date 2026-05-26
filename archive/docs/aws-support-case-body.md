# AWS Support Case 175313470800975 — Reopen body

**How to use:** click "Reopen case" on case 175313470800975 in the AWS Support Console (signed in as `ghanzo@gmail.com` / account `462170975634`). Paste the body below.

---

## Body (paste verbatim)

Hello,

This is a related case to 175313470800975 — the same situation has produced a follow-on issue I need help with.

**Recap of prior resolution:** This case was originally about reopening a self-closed AWS account so I could recover briefer.news. AWS confirmed the account closure had triggered the standard domain release process and recommended I re-register the domain instead. I followed that guidance — briefer.news is now registered in my active account `026090521469` (registered 2025-08-09, expiring 2026-08-08, auto-renew on).

**The new blocker:** The closed account left lingering CloudFront alternate-domain-name claims that I cannot remove from any account I currently access. This is preventing me from setting up CloudFront for the domain in my active deployment account.

Concretely:

- I have an active CloudFront distribution `EMV1VIFYTSI3U` in account `462170975634` at `d1sl4o5xm2ds0o.cloudfront.net`.
- I have a valid ACM certificate covering `briefer.news` and `www.briefer.news` in the same account: `arn:aws:acm:us-east-1:462170975634:certificate/bd7ce8ea-b95b-40fc-ae63-1e5f05148887` (Status: ISSUED, validated via DNS).
- When I run `aws cloudfront associate-alias --target-distribution-id EMV1VIFYTSI3U --alias briefer.news`, it fails with: *"An error occurred (IllegalUpdate) when calling the AssociateAlias operation: Invalid or missing alias DNS TXT records."*
- `aws cloudfront list-conflicting-aliases` shows the alternate domain names `briefer.news`, `www.briefer.news`, and `*.briefer.news` are still associated with distribution `******5LVBHXZ` in account `******200621`. Per the prior correspondence on this case, that account is my own self-closed AWS account.

**Request:** Please release the alternate-domain-name claims (briefer.news, www.briefer.news, *.briefer.news) from the closed account's distribution `******5LVBHXZ`, or terminate the orphaned distribution itself, so my active distribution `EMV1VIFYTSI3U` can claim them via `associate-alias`.

I have already updated the registrar's nameservers to my active account's hosted zone (`Z07630701MT6TMX2WHCGE`, NS records: `ns-1990.awsdns-56.co.uk`, `ns-1505.awsdns-60.org`, `ns-584.awsdns-09.net`, `ns-454.awsdns-56.com`) and added Route 53 alias A-records pointing `briefer.news` and `www.briefer.news` at `d1sl4o5xm2ds0o.cloudfront.net`. So once the alias claims are released, completion is just two `associate-alias` calls.

Thank you.

---

## After submitting

Tell me what AWS replies. If they confirm the release, the resolution is two CLI calls (`associate-alias` for apex + www) and we're live at https://briefer.news.
