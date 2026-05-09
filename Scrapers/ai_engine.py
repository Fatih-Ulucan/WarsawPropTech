import logging
import time
import io
import requests
import base64
import os
from PIL import Image
from Scrapers.config import MAX_AI_CALLS

logger = logging.getLogger(__name__)

class GeminiAnalyzer:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("API_KEY") or os.getenv("GROQ_API_KEY")
        self.ai_calls_made = 0

        if self.api_key:
            self.text_model = "llama-3.3-70b-versatile"
            self.vision_model = "llama-3.2-90b-vision-preview"
            self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        else:
            self.api_key = None
            logger.warning("⚠️ API_KEY not found. AI Analysis will be skipped.")

    def reset_counter(self):
        """Resets the daily/batch call counter."""
        self.ai_calls_made = 0

    def analyze_description(self, description, category="Apartment - Sale"):
        """Sends property description to Groq and returns a 5-point investment report based on category."""
        if not self.api_key:
            return "AI Analysis unavailable."

        if self.ai_calls_made >= MAX_AI_CALLS:
            logger.warning(f"⚠️ AI Skip: Limit ({MAX_AI_CALLS}) reached for this batch. Saving API costs.")
            return "AI skipped (Batch Limit Reached to save costs)."

        try:
            time.sleep(1)

            if "Rent" in category:
                prompt = f"""
        You are a Warsaw Real Estate Expert. Analyze this {category} description:
        1. CONDITION: (Ready to move in, Needs cleaning, or Needs work?)
        2. RENTAL DEMAND: (High, Med, or Low for this area/type?)
        3. TARGET TENANT: (Students, Professionals, Families, or Business?)
        4. INVESTMENT STRATEGY: (Long-term rent, Short-term/Airbnb?)
        5. URGENCY: (Motivated landlord? Open to price negotiation?)

        Provide 5 short bullet points in English. Max 600 chars.
        Description: {description[:3500]}
        """
            elif "Commercial" in category:
                prompt = f"""
        You are a Warsaw Commercial Real Estate Expert. Analyze this {category} description:
        1. CONDITION: (Ready to use, White box, or Needs adaptation?)
        2. BUSINESS POTENTIAL: (High, Med, or Low? What type of business fits best?)
        3. LOCATION/TRAFFIC: (Mentions high foot traffic, visibility, or parking?)
        4. ROI STRATEGY: (Good for leasing out or owner-operator?)
        5. URGENCY: (Motivated seller/landlord? Open to negotiation?)

        Provide 5 short bullet points in English. Max 600 chars.
        Description: {description[:3500]}
        """
            else:
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
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.text_model,
                "messages": [{"role": "user", "content": prompt}]
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()

            text = response.json()['choices'][0]['message']['content'].strip()

            if text:
                self.ai_calls_made += 1
                return text[:600]

            return "AI summary unavailable."

        except Exception as e:
            logger.error(f"AI Error: {e}")
            return "AI Analysis failed."

    def analyze_with_vision(self, description, image_urls, category="Apartment - Sale"):
        """Sends description AND property photos to Groq Vision for a visual flip analysis."""
        if not self.api_key:
            return "AI Analysis unavailable."

        if self.ai_calls_made >= MAX_AI_CALLS:
            logger.warning(f"⚠️ AI Skip: Limit ({MAX_AI_CALLS}) reached.")
            return "AI skipped (Batch Limit Reached)."

        images_to_analyze = []

        for url in image_urls[:3]:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    base64_img = base64.b64encode(response.content).decode('utf-8')
                    img_data_url = f"data:image/jpeg;base64,{base64_img}"
                    images_to_analyze.append(img_data_url)
            except Exception as e:
                logger.error(f"❌ Resim indirme hatası: {e}")

        try:
            time.sleep(1)

            if "Rent" in category:
                prompt = f"""
            You are a Warsaw Real Estate Expert. Analyze this {category} description AND the attached photos.
            
            Description: {description[:2000]}
            
            Based heavily on the PHOTOS, tell me:
            1. VISUAL CONDITION: (Is it modern, old-fashioned, or needs cleaning?)
            2. TENANT APPEAL: (Will it attract students, pros, or hard to rent?)
            3. RENTAL POTENTIAL: (High, Med, or Low?)
            
            Provide 3 short, punchy bullet points in English. Max 500 chars.
            """
            elif "Commercial" in category:
                prompt = f"""
            You are a Warsaw Commercial Real Estate Expert. Analyze this {category} description AND the attached photos.
            
            Description: {description[:2000]}
            
            Based heavily on the PHOTOS, tell me:
            1. VISUAL CONDITION: (Ready for business, needs fit-out, or poor?)
            2. SPACE LAYOUT: (Good for retail, office, or gastronomy?)
            3. COMMERCIAL POTENTIAL: (High, Med, or Low?)
            
            Provide 3 short, punchy bullet points in English. Max 500 chars.
            """
            else:
                prompt = f"""
            You are a Warsaw Real Estate Flipping Expert. Analyze this property description AND the attached photos.
            
            Description: {description[:2000]}
            
            Based heavily on the PHOTOS, tell me:
            1. VISUAL CONDITION: (Is it modern, 90s PRL style, or needs general renovation?)
            2. RENOVATION NEEDS: (What specifically looks bad? Floors, bathroom, kitchen?)
            3. FLIP POTENTIAL: (High, Med, or Low?)
            
            Provide 3 short, punchy bullet points in English. Max 500 chars.
            """

            content_parts = [{"type": "text", "text": prompt}]
            for img_data in images_to_analyze:
                content_parts.append({
                    "type": "image_url",
                    "image_url": {"url": img_data}
                })

            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            payload = {
                "model": self.vision_model,
                "messages": [{"role": "user", "content": content_parts}]
            }

            response = requests.post(self.api_url, headers=headers, json=payload, timeout=20)
            response.raise_for_status()

            text = response.json()['choices'][0]['message']['content'].strip()

            if text:
                self.ai_calls_made += 1
                return text[:500]

            return "AI visual summary unavailable."

        except Exception as e:
            logger.error(f"AI Vision Error: {e}")
            return "AI Vision Analysis failed."