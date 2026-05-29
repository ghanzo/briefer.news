# briefer.news — single source of truth for deploy / infra constants.
#
# PURE KEY=value bash assignments ONLY. No logic, no command substitution,
# no exports, no conditionals. This file is consumed two ways and must parse
# cleanly under both:
#   1. Bash:   'source scripts/lib/env.sh'            (synthesize.sh, weekly.sh, ...)
#   2. Python: scripts/lib/config.py reads it line-by-line as KEY=value
# Keeping it to bare assignments guarantees the two parsers never drift.
#
# Every value below was derived from the actual deploy commands in the
# scripts as of the dedup refactor — do not edit one consumer's copy, edit
# THIS file and every consumer follows.

# CloudFront distribution that fronts the live site (s3 -> CDN).
DIST_ID=EMV1VIFYTSI3U

# S3 bucket holding the rendered site (usa/, china/, archives, feeds, sitemap).
S3_BUCKET=briefer-news-site

# S3 bucket holding CloudFront standard access logs (read by traffic_report.py).
CF_LOGS_BUCKET=briefer-news-cf-logs

# Absolute paths to the CLIs the pipeline shells out to.
AWS=/Users/maxgoshay/.local/bin/aws
DOCKER=/usr/local/bin/docker

# Repo root.
REPO=/Users/maxgoshay/code/briefernewsapp

# AWS region for the deployment account's resources.
REGION=us-east-1

# CloudFront default domain (public site still serves here pending the CNAME
# transfer for briefer.news).
CF_DOMAIN=d1sl4o5xm2ds0o.cloudfront.net
