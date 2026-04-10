"""Post to LinkedIn or third-party services; includes safe test mode preview."""
from typing import Optional, Dict
import os
import requests
import logging
from urllib.parse import quote

logger = logging.getLogger("velank.linkedin")


class LinkedInPoster:
    def __init__(self, test_mode: Optional[bool] = None, access_token: Optional[str] = None, person_id: Optional[str] = None):
        # Allow explicit test_mode override, otherwise use environment
        if test_mode is not None:
            self.test_mode = test_mode
        else:
            self.test_mode = os.getenv("TEST_MODE", "true").lower() in ("1", "true", "yes")
        self.access_token = (access_token if access_token is not None else os.getenv("LINKEDIN_ACCESS_TOKEN"))
        self.person_id = (person_id if person_id is not None else os.getenv("LINKEDIN_PERSON_ID"))
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
            linkedin_urn = result.get("id") if isinstance(result, dict) else None
            if not linkedin_urn:
                linkedin_urn = r.headers.get("x-restli-id") or r.headers.get("X-RestLi-Id")
            if not linkedin_urn:
                location = r.headers.get("location") or r.headers.get("Location")
                if location and "/ugcPosts/" in location:
                    linkedin_urn = location.split("/ugcPosts/")[-1]
            logger.info("Posted to LinkedIn: %s", result)
            return {
                "status": "posted",
                "response": result,
                "linkedin_urn": linkedin_urn,
                "provider": "linkedin"
            }
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

    def fetch_post_analytics(self, linkedin_urn: str) -> Dict[str, object]:
        """Fetch social action metrics for a LinkedIn post URN when API permissions allow it."""
        if not linkedin_urn:
            raise ValueError("linkedin_urn is required")
        if not self.access_token:
            raise RuntimeError("LinkedIn access token not configured")

        encoded_urn = quote(str(linkedin_urn), safe='')
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }

        endpoints = [
            (f"https://api.linkedin.com/v2/socialActions/{encoded_urn}", headers),
            (
                f"https://api.linkedin.com/rest/socialActions/{encoded_urn}",
                {
                    **headers,
                    "LinkedIn-Version": os.getenv("LINKEDIN_API_VERSION", "202401"),
                },
            ),
        ]

        response = None
        payload = {}
        forbidden_attempts = 0
        not_found_attempts = 0
        last_error = None

        for url, req_headers in endpoints:
            try:
                response = requests.get(url, headers=req_headers, timeout=30)
            except Exception as exc:
                last_error = str(exc)
                continue

            if response.status_code == 403:
                forbidden_attempts += 1
                continue
            if response.status_code == 404:
                not_found_attempts += 1
                continue
            if response.status_code >= 400:
                last_error = f"LinkedIn response {response.status_code}: {response.text[:180]}"
                continue

            payload = response.json() if response.content else {}
            break

        if not payload:
            if forbidden_attempts == len(endpoints):
                return {
                    "status": "forbidden",
                    "linkedin_urn": linkedin_urn,
                    "error": "Token/app lacks LinkedIn permission to read social analytics for this post."
                }
            if not_found_attempts == len(endpoints):
                return {
                    "status": "not_found",
                    "linkedin_urn": linkedin_urn,
                    "error": "LinkedIn post URN not found or not accessible with current token."
                }
            return {
                "status": "error",
                "linkedin_urn": linkedin_urn,
                "error": last_error or "Unable to fetch analytics from LinkedIn right now."
            }

        total_counts = payload.get("totalSocialActivityCounts") if isinstance(payload.get("totalSocialActivityCounts"), dict) else {}
        likes_summary = payload.get("likesSummary") if isinstance(payload.get("likesSummary"), dict) else {}
        comments_summary = payload.get("commentsSummary") if isinstance(payload.get("commentsSummary"), dict) else {}

        likes = total_counts.get("numLikes")
        if likes is None:
            likes = likes_summary.get("totalLikes")

        comments = total_counts.get("numComments")
        if comments is None:
            comments = comments_summary.get("totalFirstLevelComments")

        shares = total_counts.get("numShares")

        def to_int(value):
            try:
                return int(value)
            except Exception:
                return 0

        likes_i = to_int(likes)
        comments_i = to_int(comments)
        shares_i = to_int(shares)

        return {
            "status": "ok",
            "linkedin_urn": linkedin_urn,
            "likes": likes_i,
            "comments": comments_i,
            "shares": shares_i,
            "interactions": likes_i + comments_i + shares_i,
            "raw": payload,
        }


if __name__ == "__main__":
    import dotenv, logging
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    poster = LinkedInPoster()
    sample = "Hook line\n\nBody paragraph.\n\nCTA: Reply if you'd like help. #VirtualAssistant #Productivity"
    print(poster.post(sample))
