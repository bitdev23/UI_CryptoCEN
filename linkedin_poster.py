"""Post to LinkedIn or third-party services; includes safe test mode preview."""
from typing import Optional, Dict
import os
import requests
import logging

logger = logging.getLogger("valtrilabs.linkedin")


class LinkedInPoster:
    def __init__(self, test_mode: Optional[bool] = None):
        # Allow explicit test_mode override, otherwise use environment
        if test_mode is not None:
            self.test_mode = test_mode
        else:
            self.test_mode = os.getenv("TEST_MODE", "true").lower() in ("1", "true", "yes")
        self.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN")
        self.person_id = os.getenv("LINKEDIN_PERSON_ID")
        self.ayrshare_key = os.getenv("AYRSHARE_API_KEY")
        self.buffer_token = os.getenv("BUFFER_ACCESS_TOKEN")

    def post_text_linkedin(self, text: str) -> Dict[str, str]:
        """Post text to LinkedIn using the v2 UGC API. Returns response info."""
        if self.test_mode:
            logger.info("Test mode enabled — preview only\n%s", text)
            return {"status": "preview", "content": text}
        if not self.access_token or not self.person_id:
            raise RuntimeError("LinkedIn access token or person id not configured")
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
        # Build author URN for personal profile
        author = self.person_id if self.person_id.startswith("urn:") else f"urn:li:person:{self.person_id}"
        payload = {
            "author": author,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=30)
            r.raise_for_status()
            result = r.json()
            logger.info("Posted to LinkedIn: %s", result)
            return {"status": "posted", "response": result}
        except requests.exceptions.HTTPError as e:
            logger.error("LinkedIn API error: %s - %s", e.response.status_code, e.response.text)
            raise
        except Exception:
            logger.exception("Failed to post to LinkedIn")
            raise

    def post_via_ayrshare(self, text: str) -> Dict[str, str]:
        if self.test_mode:
            logger.info("Test mode — Ayrshare preview\n%s", text)
            return {"status": "preview", "content": text}
        if not self.ayrshare_key:
            raise RuntimeError("AYRSHARE_API_KEY not configured")
        url = "https://app.ayrshare.com/api/v1/post"
        headers = {"Authorization": f"Bearer {self.ayrshare_key}", "Content-Type": "application/json"}
        payload = {"post": text, "platforms": ["linkedin"], "media": []}
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=30)
            r.raise_for_status()
            return {"status": "posted", "response": r.json()}
        except Exception:
            logger.exception("Ayrshare post failed")
            raise

    def post(self, text: str, via: Optional[str] = None) -> Dict[str, str]:
        if via == "ayrshare":
            return self.post_via_ayrshare(text)
        elif via == "buffer":
            # Buffer integration placeholder — requires OAuth token
            logger.info("Buffer posting not implemented; falling back to LinkedIn API")
            return self.post_text_linkedin(text)
        else:
            return self.post_text_linkedin(text)


if __name__ == "__main__":
    import dotenv, logging
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    poster = LinkedInPoster()
    sample = "Hook line\n\nBody paragraph.\n\nCTA: Reply if you'd like help. #VirtualAssistant #Productivity"
    print(poster.post(sample))
