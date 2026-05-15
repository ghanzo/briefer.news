// CloudFront Function for briefer-news (briefer-news-index-rewrite)
// Distribution: EMV1VIFYTSI3U
// Runtime: cloudfront-js-2.0
// Event type: viewer-request
//
// Two jobs:
//   1. Root-path smart edition routing — cookie-based memory (return
//      visitor to their last edition) with a geo-based default fallback
//      (Asia → /china/, else → /usa/). Briefly removed 2026-05-14 to
//      surface the selector; restored later that day per user preference
//      for zero-friction landing.
//   2. URL rewriting for non-root paths — trailing-slash → index.html,
//      extensionless → /index.html.

function handler(event) {
    var request = event.request;
    var uri = request.uri;
    var headers = request.headers;
    var cookies = request.cookies;

    // Root path: smart edition routing
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

    // Non-root: trailing-slash + extensionless rewrites
    if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
    } else if (!uri.includes('.')) {
        request.uri = uri + '/index.html';
    }

    return request;
}
