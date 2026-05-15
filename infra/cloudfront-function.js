// CloudFront Function for briefer-news (briefer-news-index-rewrite)
// Distribution: EMV1VIFYTSI3U
// Runtime: cloudfront-js-2.0
// Event type: viewer-request
//
// Job: rewrite directory-style URLs to their index.html (no redirect dance,
// just rewrite at the edge). Previously this also handled root-path 302
// redirects to /usa/ or /china/ based on cookie + geo; that logic was
// removed 2026-05-14 so visitors to briefer.news/ actually see the
// selector page (which fetches both editions' headlines live).

function handler(event) {
    var request = event.request;
    var uri = request.uri;

    // Trailing-slash → index.html  (e.g., /usa/  → /usa/index.html)
    if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
    }
    // Extension-less paths → /index.html  (e.g., /about → /about/index.html)
    else if (!uri.includes('.')) {
        request.uri = uri + '/index.html';
    }

    return request;
}
