import { useState } from 'react'
import Modal from './Modal'

const guides = {
  instagram: {
    title: 'Instagram',
    steps: [
      'Switch your Instagram account to a professional account (Business or Creator).',
      'Create a Meta developer app and choose Instagram API setup with Instagram Login. This route does not require linking a Facebook Page.',
      'Add your own professional account in the app’s setup flow. Accept any tester invitation if the app is in development mode.',
      'Authorize the account and obtain an Instagram user access token using the dashboard setup or the official Instagram Login flow. Include instagram_business_basic for profile access.',
      'Save the token as INSTAGRAM_ACCESS_TOKEN. Set META_GRAPH_VERSION to the supported Graph API version selected for your app. Use an Instagram Login token, not a Facebook token.',
    ],
    config: 'INSTAGRAM_ACCESS_TOKEN=your_instagram_user_token\nMETA_GRAPH_VERSION=your_supported_version',
    url: 'https://www.postman.com/meta/instagram/folder/6raa77c/instagram-api-with-instagram-login',
    console: 'https://developers.facebook.com/apps/',
  },
  facebook: {
    title: 'Facebook Page',
    steps: [
      'Create a Facebook Page and make sure your Facebook account has access to manage it.',
      'Create or select a Meta developer app with the Pages use case. Add yourself to the app’s roles for development testing.',
      'Use Meta’s Graph API Explorer with your app to authorize your user account. Request pages_show_list and the Page read permissions needed for your app, such as pages_read_engagement.',
      'Retrieve the Pages you manage using GET /me/accounts with fields=id,name,access_token. Select the intended Page and use its returned Page access token, not the original user token.',
      'Save the matching Page ID and Page token below. Set META_GRAPH_VERSION to a supported version for your app. Variance checks that the token identifies this exact Page.',
    ],
    config: 'FACEBOOK_PAGE_ID=your_numeric_page_id\nFACEBOOK_PAGE_ACCESS_TOKEN=your_page_token\nMETA_GRAPH_VERSION=your_supported_version',
    url: 'https://www.postman.com/meta/facebook/request/tass6hw/get-specific-page-access-token',
    console: 'https://developers.facebook.com/tools/explorer/',
  },
  threads: {
    title: 'Threads',
    steps: [
      'Create your Threads profile and register a Meta developer app with the Threads API use case.',
      'Add your Threads account as a tester when using development mode, and accept the invitation from that account.',
      'Follow the Threads app setup or official authorization flow to authorize your profile with threads_basic access.',
      'Obtain a Threads user access token. If you exchange it for a longer-lived token, follow Meta’s current token instructions and keep track of its expiry.',
      'Save it as THREADS_ACCESS_TOKEN. Your Instagram or Facebook token cannot replace this token.',
    ],
    config: 'THREADS_ACCESS_TOKEN=your_threads_user_token',
    url: 'https://www.postman.com/meta/threads/documentation/dht3nzz/threads-api',
    console: 'https://developers.facebook.com/apps/',
  },
  x: {
    title: 'X (Twitter)',
    steps: [
      'Create a developer account and app in the X Developer Console. Review API access requirements and costs for your account.',
      'Enable OAuth 2.0 in the app’s user authentication settings. Register the exact callback URL used by your OAuth client.',
      'Use an OAuth client that supports Authorization Code with PKCE. Configure its Client ID, matching callback URL, and tweet.read and users.read scopes, then authorize your X account.',
      'Exchange the authorization code through that client to obtain an OAuth 2.0 user access token. Variance does not yet host an OAuth callback; do not use its localhost homepage as one.',
      'Save the access token as X_USER_ACCESS_TOKEN. Do not use the app-only bearer token, API key, client secret or refresh token. Automatic token renewal is not implemented in Variance.',
    ],
    config: 'X_USER_ACCESS_TOKEN=your_oauth2_user_access_token',
    url: 'https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code',
    console: 'https://developer.x.com/',
  },
}

export default function SocialSetupGuide({ close }: { close: () => void }) {
  const [platform, setPlatform] = useState<keyof typeof guides>('instagram')
  const guide = guides[platform]
  return <Modal title="Connect your social accounts." eyebrow="STEP-BY-STEP SETUP" close={close}>
    <div className="social-setup-guide">
      <p>Choose a platform, create its developer app, then add its credentials locally. You can connect one platform at a time.</p>
      <div className="social-guide-platforms" role="group" aria-label="Choose setup platform">{Object.entries(guides).map(([key, value]) => <button type="button" className="secondary small" aria-pressed={platform === key} key={key} onClick={() => setPlatform(key as keyof typeof guides)}>{value.title}</button>)}</div>
      <h3>{guide.title} setup</h3>
      <ol>{guide.steps.map(step => <li key={step}>{step}</li>)}</ol>
      <div className="social-guide-links"><a href={guide.console} target="_blank" rel="noopener noreferrer">Open developer tools ↗</a><a href={guide.url} target="_blank" rel="noopener noreferrer">Official setup instructions ↗</a></div>
      <h3>Add your local settings</h3>
      <p>Open <code>.env</code> in the Variance project folder. If it is missing, copy <code>.env.example</code> first. Update these entries without overwriting your existing keys:</p>
      <pre><code>{guide.config}</code></pre>
      <p>Replace the placeholders with your own values. For Meta, use a version such as <code>v25.0</code> only if your app supports it. Never put tokens in frontend code or Git.</p>
      <h3>Restart and verify</h3>
      <ol><li>Save <code>.env</code> and stop the backend with Ctrl+C.</li><li>From the <code>backend</code> folder, run:<pre><code>uv run uvicorn app.main:app --host 127.0.0.1 --port 8765</code></pre></li><li>Return to Settings → Your social connections. Click <strong>Refresh configuration</strong>, then <strong>Check connection</strong> on the platform card.</li><li>Confirm that the returned account name and ID match the account you intended to connect.</li></ol>
      <details><summary>Connection not working?</summary><ul><li><strong>Setup needed:</strong> check the required entries, filename (.env, not .env.txt), and restart.</li><li><strong>Token rejected:</strong> check expiry, token type, permissions and app roles. Reauthorize if needed.</li><li><strong>Wrong Facebook Page:</strong> use a Page token matching FACEBOOK_PAGE_ID.</li><li><strong>Rate limit or access-plan error:</strong> check the provider dashboard before retrying.</li></ul></details>
      <p className="discovery-message">This setup verifies account identity only. Live publishing and automatic token refresh are not enabled. Developer dashboard labels may change; use the linked official instructions if a step looks different.</p>
      <button className="primary" onClick={close}>Got it</button>
    </div>
  </Modal>
}
