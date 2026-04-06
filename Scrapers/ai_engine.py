import google.generativeai as genai
import logging
import time
from Scrapers.config import MAX_AI_CALLS

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.ai_calls_made = 0
        if api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('models/gemini-2.5-flash')
        else:
            self.model = None
            logger.warning("⚠️ GEMINI_API_KEY not found. AI Analysis will be skipped.")

    def reset_counter(self):
        """Resets the daily/batch call counter."""
        self.ai_calls_made = 0

    def analyze_description(self, description):
        """Sends property description to Gemini and returns a 5-point investment report."""
        if not self.model:
            return "AI Analysis unavailable."

        if self.ai_calls_made >= MAX_AI_CALLS:
            logger.warning(f"⚠️ AI Skip: Limit ({MAX_AI_CALLS}) reached for this batch. Saving API costs.")
            return "AI skipped (Batch Limit Reached to save costs)."

        try:
            time.sleep(1)

            prompt = f"""
        You are a Warsaw Real Estate Investment Expert. Analyze this Polish description:
        1. CONDITION: (Renovated, New, or Needs Work?)
        2. FLIP POTENTIAL: (High, Med, or Low?)
        3. MARKET SPEED: (Estimate: <7 days, 2 weeks, or 1+ month?)
        4. INVESTMENT STRATEGY: (Buy-to-let or Quick Flip?)
        5. URGENCY: (Motivated seller? Mentions quick sale, leaving country, or open to negotiation?)

        Provide 5 short bullet points in English. Max 600 chars.
        Description: {description[:3500]}
        """

            response = self.model.generate_content(prompt)
            text = response.text.strip()

            if text:
                self.ai_calls_made += 1
                return text[:600]

            return "AI summary unavailable."

        except Exception as e:
            logger.error(f"AI Error: {e}")
            return "AI Analysis failed."