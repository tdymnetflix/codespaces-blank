# Temporary Hermes WebUI Link

**Public URL:** https://systematic-photographer-realistic-deadline.trycloudflare.com

This is an unauthenticated Cloudflare Quick Tunnel to the local Hermes WebUI at `localhost:8787`. Anyone with this URL may access the WebUI and its agent capabilities.

The URL is temporary and will stop working when the local `cloudflared` process exits. Do not commit long-lived secrets or use this link for production access.

Started with:

```bash
./bin/cloudflared tunnel --url http://127.0.0.1:8787
```
