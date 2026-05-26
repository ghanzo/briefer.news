// CloudFront Function for briefer-news (briefer-news-index-rewrite)
// Distribution: EMV1VIFYTSI3U
// Runtime: cloudfront-js-2.0
// Event type: viewer-request
//
// Three jobs:
//   0. Canonical-host enforcement — 301 www.briefer.news/* → briefer.news/*
//      so Google indexes a single hostname (added 2026-05-26 after the
//      morning brief showed www and non-www splitting impressions).
//   1. Root-path smart edition routing — cookie-based memory (return
//      visitor to their last edition) with a geo-based default fallback
//      (Asia → /china/, else → /usa/).
//   2. URL rewriting for non-root paths — trailing-slash → index.html,
//      extensionless → /index.html.

function handler(event) {
    var request = event.request;
    var uri = request.uri;
    var headers = request.headers;
    var cookies = request.cookies;

    // ── Job 0: canonical-host (www → non-www) ──────────────────────────────
    var host = (headers['host'] && headers['host'].value) || '';
    if (host.indexOf('www.') === 0) {
        var canonicalHost = host.substring(4); // strip leading "www."
        // Preserve query string if present
        var qs = '';
        if (request.querystring) {
            var parts = [];
            for (var k in request.querystring) {
                var v = request.querystring[k];
                if (v.value !== undefined) parts.push(k + '=' + v.value);
                if (v.multiValue) {
                    for (var i = 0; i < v.multiValue.length; i++) {
                        parts.push(k + '=' + v.multiValue[i].value);
                    }
                }
            }
            if (parts.length) qs = '?' + parts.join('&');
        }
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: { 'location': { value: 'https://' + canonicalHost + uri + qs } }
        };
    }

    // ── Job 1: root-path smart edition routing ─────────────────────────────
    if (uri === '/' || uri === '/index.html') {
        // Cookie override wins (last-edition memory)
        var editionCookie = (cookies['briefer-edition'] && cookies['briefer-edition'].value) || '';
        if (editionCookie === 'usa' || editionCookie === 'china') {
            return {
                statusCode: 302,
                statusDescription: 'Found',
                headers: { 'location': { value: '/' + editionCookie + '/' } }
            };
        }

        // Geo-based default
        var country = (headers['cloudfront-viewer-country'] && headers['cloudfront-viewer-country'].value) || '';
        var edition = 'usa';
        if (country === 'CN' || country === 'HK' || country === 'TW' ||
            country === 'SG' || country === 'JP' || country === 'KR') {
            edition = 'china';
        }
        return {
            statusCode: 302,
            statusDescription: 'Found',
            headers: { 'location': { value: '/' + edition + '/' } }
        };
    }

    // Legacy /og-week/ → /weekly/ — Outside the Gate was removed 2026-05-14.
    // Permanent redirect protects any external links or bookmarks.
    if (uri === '/usa/og-week/' || uri === '/usa/og-week' || uri === '/usa/og-week/index.html') {
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: { 'location': { value: '/usa/weekly/' } }
        };
    }
    if (uri === '/china/og-week/' || uri === '/china/og-week' || uri === '/china/og-week/index.html') {
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: { 'location': { value: '/china/weekly/' } }
        };
    }

    // ── Job 2: non-root rewrites — trailing-slash + extensionless ─────────
    if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
    } else if (!uri.includes('.')) {
        request.uri = uri + '/index.html';
    }

    return request;
}
